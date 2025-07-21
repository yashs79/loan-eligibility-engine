document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const fileInput = document.getElementById('csv-file');
    const fileLabel = document.getElementById('file-label');
    const fileDetails = document.getElementById('file-details');
    const uploadButton = document.getElementById('upload-button');
    const statusMessage = document.getElementById('status-message');
    const progressBar = document.getElementById('progress-bar');
    const historyList = document.getElementById('history-list');
    const fileInputWrapper = document.querySelector('.file-input-wrapper');

    // Variables
    let selectedFile = null;
    let uploadHistory = JSON.parse(localStorage.getItem('uploadHistory') || '[]');

    // Initialize the page
    initPage();

    // Event Listeners
    fileInput.addEventListener('change', handleFileSelect);
    uploadButton.addEventListener('click', handleUpload);
    
    // Drag and drop functionality
    fileInputWrapper.addEventListener('dragover', (e) => {
        e.preventDefault();
        fileInputWrapper.classList.add('dragover');
    });
    
    fileInputWrapper.addEventListener('dragleave', () => {
        fileInputWrapper.classList.remove('dragover');
    });
    
    fileInputWrapper.addEventListener('drop', (e) => {
        e.preventDefault();
        fileInputWrapper.classList.remove('dragover');
        
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            handleFileSelect();
        }
    });

    // Functions
    function initPage() {
        // Display upload history
        updateHistoryList();
    }

    function handleFileSelect() {
        if (fileInput.files.length > 0) {
            selectedFile = fileInput.files[0];
            
            // Validate file type
            if (!selectedFile.name.toLowerCase().endsWith('.csv')) {
                showError('Please select a CSV file');
                resetFileInput();
                return;
            }
            
            // Update UI
            const fileSizeInMB = (selectedFile.size / (1024 * 1024)).toFixed(2);
            fileDetails.innerHTML = `
                <p><strong>File:</strong> ${selectedFile.name}</p>
                <p><strong>Size:</strong> ${fileSizeInMB} MB</p>
                <p><strong>Last Modified:</strong> ${new Date(selectedFile.lastModified).toLocaleString()}</p>
            `;
            fileDetails.classList.add('has-file');
            uploadButton.disabled = false;
            
            // Update file label
            document.querySelector('.file-text').textContent = 'File selected';
        }
    }

    function handleUpload() {
        if (!selectedFile) {
            showError('Please select a file first');
            return;
        }
        
        // Update UI to show upload in progress
        uploadButton.disabled = true;
        statusMessage.textContent = 'Uploading file...';
        progressBar.style.width = '0%';
        
        // Create a unique file key
        const timestamp = new Date().getTime();
        const fileKey = `uploads/${timestamp}-${selectedFile.name}`;
        
        // Initialize S3 upload
        const s3 = new AWS.S3({
            params: { Bucket: awsConfig.bucketName }
        });
        
        const params = {
            Key: fileKey,
            Body: selectedFile,
            ContentType: 'text/csv'
        };
        
        // Perform the upload
        const upload = s3.upload(params);
        
        // Track upload progress
        upload.on('httpUploadProgress', (progress) => {
            const percentage = Math.round((progress.loaded / progress.total) * 100);
            progressBar.style.width = `${percentage}%`;
            statusMessage.textContent = `Uploading: ${percentage}%`;
        });
        
        // Handle upload completion
        upload.send((err, data) => {
            if (err) {
                console.error('Upload error:', err);
                statusMessage.textContent = `Upload failed: ${err.message}`;
                uploadButton.disabled = false;
                return;
            }
            
            // Update UI for successful upload
            statusMessage.textContent = 'Upload completed successfully!';
            progressBar.style.width = '100%';
            
            // Add to upload history
            addToHistory(selectedFile.name, data.Location);
            
            // Reset file input after successful upload
            setTimeout(() => {
                resetFileInput();
                statusMessage.textContent = 'Ready for next upload';
                progressBar.style.width = '0%';
            }, 3000);
        });
    }

    function resetFileInput() {
        fileInput.value = '';
        selectedFile = null;
        fileDetails.innerHTML = '<p>No file selected</p>';
        fileDetails.classList.remove('has-file');
        uploadButton.disabled = true;
        document.querySelector('.file-text').textContent = 'Choose a CSV file or drag it here';
    }

    function showError(message) {
        statusMessage.textContent = message;
        statusMessage.style.color = 'var(--error-color)';
        
        setTimeout(() => {
            statusMessage.textContent = 'No active uploads';
            statusMessage.style.color = '';
        }, 3000);
    }

    function addToHistory(fileName, fileUrl) {
        const timestamp = new Date().toLocaleString();
        
        // Add to history array
        uploadHistory.unshift({
            fileName,
            fileUrl,
            timestamp,
            date: new Date().toISOString()
        });
        
        // Keep only the last 10 uploads
        if (uploadHistory.length > 10) {
            uploadHistory = uploadHistory.slice(0, 10);
        }
        
        // Save to local storage
        localStorage.setItem('uploadHistory', JSON.stringify(uploadHistory));
        
        // Update the UI
        updateHistoryList();
    }

    function updateHistoryList() {
        if (uploadHistory.length === 0) {
            historyList.innerHTML = '<li>No upload history</li>';
            return;
        }
        
        historyList.innerHTML = '';
        uploadHistory.forEach(item => {
            const li = document.createElement('li');
            li.innerHTML = `
                <span>${item.fileName}</span>
                <span class="history-date">${item.timestamp}</span>
            `;
            historyList.appendChild(li);
        });
    }
});
