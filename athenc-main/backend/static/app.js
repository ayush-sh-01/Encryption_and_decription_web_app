// ==================== STATE MANAGEMENT ====================
let currentMode = 'encrypt';
let selectedFile = null;

// ==================== DOM ELEMENTS ====================
const modeButtons = document.querySelectorAll('.mode-btn');
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const fileNameDisplay = document.getElementById('fileName');
const passwordInput = document.getElementById('password');
const togglePassword = document.getElementById('togglePassword');
const submitBtn = document.getElementById('submitBtn');
const btnText = document.getElementById('btnText');
const notification = document.getElementById('notification');
const loadingOverlay = document.getElementById('loadingOverlay');

// Helper to show notifications
function showNotification(message, type = 'info') {
    notification.textContent = message;
    notification.className = `notification ${type}`;
    notification.style.display = 'block';
    setTimeout(() => {
        notification.style.display = 'none';
    }, 5000);
}

// ==================== MODE SWITCHING ====================
modeButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        // Update active state
        modeButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        // Update current mode
        currentMode = btn.dataset.mode;
        
        // Clear file when switching mode to avoid confusion
        selectedFile = null;
        fileInput.value = '';
        fileNameDisplay.textContent = 'Drag & drop a file or click to upload';
        submitBtn.disabled = true;

        // Update button and header text
        const header = document.querySelector('.hero h1');
        if (currentMode === 'encrypt') {
            btnText.textContent = '🔒 Encrypt File';
            header.textContent = 'Secure File Encryption';
        } else {
            btnText.textContent = '🔓 Decrypt File';
            header.textContent = 'File Decryption';
        }
    });
});

// ==================== FILE HANDLING ====================
// Open file dialog when upload area is clicked
uploadArea.addEventListener('click', () => fileInput.click());

// Handle file selection
fileInput.addEventListener('change', (e) => {
    selectedFile = e.target.files[0];
    if (selectedFile) {
        fileNameDisplay.textContent = `File Selected: ${selectedFile.name}`;
        submitBtn.disabled = false;
    } else {
        fileNameDisplay.textContent = 'Drag & drop a file or click to upload';
        submitBtn.disabled = true;
    }
});

// Optional: Drag and drop listeners
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('drag-over');
});
uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('drag-over');
});
uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
    fileInput.files = e.dataTransfer.files;
    fileInput.dispatchEvent(new Event('change')); // Trigger change event
});


// ==================== PASSWORD TOGGLE ====================
togglePassword.addEventListener('click', () => {
    const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
    passwordInput.setAttribute('type', type);
});

// ==================== FORM SUBMISSION & API INTEGRATION ====================
submitBtn.addEventListener('click', (e) => {
    e.preventDefault();
    if (selectedFile && passwordInput.value) {
        processFile(selectedFile, passwordInput.value, currentMode);
    } else {
        showNotification('Please select a file and enter a password.', 'error');
    }
});

/**
 * 🚀 Handles sending the file and password to the Python backend API.
 */
async function processFile(file, password, mode) {
    // 1. Show loading indicator and disable form
    loadingOverlay.style.display = 'flex';
    submitBtn.disabled = true;

    // Use the correct endpoint for FastAPI
    const endpoint = mode === 'encrypt' ? '/encrypt' : '/decrypt';
    
    // FormData is required to send files and forms together
    const formData = new FormData();
    formData.append('file', file);       // Must match FastAPI's 'file: UploadFile = File(...)'
    formData.append('password', password); // Must match FastAPI's 'password: str = Form(...)'

    try {
        // 2. Make the API call
        const response = await fetch(endpoint, {
            method: 'POST',
            body: formData, // Fetch handles setting Content-Type for FormData
        });

        // 3. Handle Errors (e.g., 400 Bad Password or 500 Server Error)
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Unknown server error occurred.');
        }
        
        // 4. Handle success and download the resulting file
        
        // Try to get the suggested filename from the header
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = (mode === 'encrypt' ? file.name + '.enc' : file.name.replace('.enc', ''));
        if (contentDisposition && contentDisposition.indexOf('filename=') !== -1) {
            // Extract the filename from the header
            filename = contentDisposition.split('filename=')[1].trim().replace(/['"]/g, '');
        }

        // Get the response as a file (Blob)
        const blob = await response.blob();
        
        // Create a temporary link element to trigger the download
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        
        // Clean up the temporary link and URL object
        a.remove();
        window.URL.revokeObjectURL(url);

        showNotification(`${mode === 'encrypt' ? 'Encryption' : 'Decryption'} successful! File downloaded as "${filename}".`, 'success');

    } catch (error) {
        console.error('API Error:', error);
        showNotification(`Failed to process file: ${error.message || 'Check console for details.'}`, 'error');
    } finally {
        // 5. Clean up UI
        loadingOverlay.style.display = 'none';
        submitBtn.disabled = false;
        // Optional: Reset form fields here
        passwordInput.value = '';
    }
}