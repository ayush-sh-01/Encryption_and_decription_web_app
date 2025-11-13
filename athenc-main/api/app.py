from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
import os
import io
import zipfile
import logging
import secrets
import tempfile
from typing import IO

# Cryptography imports
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

app = FastAPI()

# Logging for diagnostics
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CORE CONFIGURATION ---

# IMPORTANT: Ensure your project structure has a 'static' folder 
# containing index.html, app.js, and any CSS files.
app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS setup (allows your frontend to talk to your backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for local testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
SALT_SIZE = 16
NONCE_SIZE = 12
KDF_ITERATIONS = 200000

# --- HELPER FUNCTIONS (Your Cryptography Logic) ---

def derive_key(password: str, salt: bytes) -> bytes:
    """Derives a cryptographic key from the user's password using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=KDF_ITERATIONS,
        backend=default_backend()
    )
    return kdf.derive(password.encode())

# --- ROUTES ---

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serves the main frontend page (index.html)."""
    # NOTE: Assuming static/index.html exists relative to app.py
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="index.html not found in static folder.")


@app.post("/encrypt")
async def encrypt(file: UploadFile = File(...), password: str = Form(...)):
    """Encrypts the uploaded file (wrapped in a zip) using AES-GCM."""
    if not password:
        raise HTTPException(status_code=400, detail="Password required")

    # 1. Read and ZIP file in memory
    data = await file.read()
    zip_buffer = io.BytesIO()
    # Compress the original file inside a zip archive before encryption
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(file.filename or "file", data)
    plain = zip_buffer.getvalue()

    # 2. Key Derivation and Encryption
    salt = secrets.token_bytes(SALT_SIZE)
    key = derive_key(password, salt)
    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(NONCE_SIZE)
    # Encrypt the zipped bytes
    ct = aesgcm.encrypt(nonce, plain, None)

    # 3. Create output file (salt + nonce + ciphertext)
    out = salt + nonce + ct
    
    # 4. Prepare File Response
    output_filename = (file.filename or "uploaded_file") + ".enc"
    
    # Use StreamingResponse to stream the bytes directly from memory without saving to a temp file
    # for better performance and security.
    return StreamingResponse(
        io.BytesIO(out),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename=\"{output_filename}\"",
            "Content-Length": str(len(out))
        }
    )


@app.post("/decrypt")
async def decrypt(file: UploadFile = File(...), password: str = Form(...)):
    """Decrypts the uploaded file, extracts the contents from the zip, and returns the original file."""
    if not password:
        raise HTTPException(status_code=400, detail="Password required")

    data = await file.read()
    if len(data) < SALT_SIZE + NONCE_SIZE + 1:
        raise HTTPException(status_code=400, detail="Invalid encrypted file format or size.")

    # 1. Extract salt, nonce, and ciphertext
    salt = data[:SALT_SIZE]
    nonce = data[SALT_SIZE:SALT_SIZE+NONCE_SIZE]
    ct = data[SALT_SIZE+NONCE_SIZE:]

    # 2. Key Derivation and Decryption
    key = derive_key(password, salt)
    aesgcm = AESGCM(key)
    try:
        # Decrypt the ciphertext to get the original zipped bytes
        plain = aesgcm.decrypt(nonce, ct, None)
    except Exception as e:
        logger.exception("Decryption failed: %s", str(e))
        raise HTTPException(status_code=403, detail="Decryption failed. Bad password or corrupted file.")

    # 3. Unzip and extract the original file
    zip_buffer = io.BytesIO(plain)
    try:
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            namelist = zf.namelist()
            if not namelist:
                raise HTTPException(status_code=400, detail="Decrypted content is an empty zip archive.")
            
            # We assume the first file in the zip is the original file
            original_filename = os.path.basename(namelist[0])
            extracted = zf.read(namelist[0])

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Decrypted content is not a valid zip file.")
    
    # 4. Return the original file
    return StreamingResponse(
        io.BytesIO(extracted),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename=\"{original_filename}\"",
            "Content-Length": str(len(extracted))
        }
    )

# ✅ Add this at the bottom of app.py (for Vercel serverless entry)
handler = app

if __name__ == '__main__':
    import uvicorn
    # NOTE: Run with 'uvicorn app:app --reload' in a terminal for better development
    uvicorn.run(app, host="0.0.0.0", port=8000)