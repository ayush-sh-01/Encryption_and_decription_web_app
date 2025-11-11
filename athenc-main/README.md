# Encrypt/Decrypt App

This is a minimal example application: a Python (FastAPI) backend and a tiny React frontend (served as static files) that lets you encrypt and decrypt files using AES-GCM with a password (PBKDF2 key derivation).

## Requirements
- Python 3.8+
- On Windows PowerShell

## Install
Open PowerShell in `d:\ath\backend` and run:

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
```

## Run

```powershell
# from d:\ath\backend
.\.venv\Scripts\Activate.ps1; uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Then open http://127.0.0.1:8000/ in your browser.

## Notes
- Encryption format: salt(16 bytes) || nonce(12 bytes) || ciphertext
- The backend compresses the uploaded file into a zip before encryption so multiple files can be supported later.
- This is a simple demo; do not use for high-security production without review.

## One-step run (Windows PowerShell)

There's a helper script `run_server.ps1` that will create/activate a venv, install requirements, and start the server.

Run from `d:\ath\backend`:

```powershell
# This will prompt if packages need installing and then start the dev server
.\run_server.ps1
```
