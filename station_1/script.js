// DOM Elements
const modal = document.getElementById('cameraModal');
const closeButton = document.querySelector('.close-button');
const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const captureButton = document.getElementById('captureButton');
const cameraSelect = document.getElementById('cameraSelect');
const tiles = document.querySelectorAll('.tile');

let currentSymbol = '';
let stream = null;

// Symbol to folder name mapping
const symbolToFolder = {
    '🌟': 'star',
    '🌈': 'rainbow',
    '🌺': 'flower',
    '🦋': 'butterfly',
    '🐬': 'dolphin',
    '🦁': 'lion',
    '🐘': 'elephant',
    '🦒': 'giraffe',
    '🦊': 'fox',
    '🐼': 'panda',
    '🐢': 'turtle',
    '🦉': 'owl',
    '🦄': 'unicorn',
    '🐠': 'fish',
    '🦚': 'peacock'
};

// Get available cameras and populate the dropdown
async function getCameraDevices() {
    try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoDevices = devices.filter(device => device.kind === 'videoinput');
        
        // Clear existing options
        cameraSelect.innerHTML = '';
        
        // Add options for each camera
        videoDevices.forEach(device => {
            const option = document.createElement('option');
            option.value = device.deviceId;
            option.text = device.label || `Camera ${cameraSelect.length + 1}`;
            cameraSelect.appendChild(option);
        });

        // If no camera label is available, we need to initialize a stream first
        if (videoDevices.length > 0 && !videoDevices[0].label) {
            await initializeCamera();
            await getCameraDevices(); // Retry after getting labels
        }
    } catch (err) {
        console.error('Error getting camera devices:', err);
    }
}

// Initialize camera access
async function initializeCamera() {
    try {
        // Stop any existing stream
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
        }

        // Get the selected camera ID, or use the default one
        const deviceId = cameraSelect.value;
        
        const constraints = {
            video: {
                deviceId: deviceId ? { exact: deviceId } : undefined,
                facingMode: deviceId ? undefined : 'environment',
                width: { ideal: 1280 },
                height: { ideal: 720 }
            }
        };

        stream = await navigator.mediaDevices.getUserMedia(constraints);
        video.srcObject = stream;

        // If this is the first time getting camera access, populate the dropdown
        if (cameraSelect.options.length === 0) {
            await getCameraDevices();
        }
    } catch (err) {
        console.error('Error accessing camera:', err);
        alert('Unable to access camera. Please make sure you have granted camera permissions.');
    }
}

// Save image to file
async function saveImage(imageData, folderName) {
    try {
        // Convert base64 to blob
        const base64Data = imageData.split(',')[1];
        const blob = await fetch(`data:image/jpeg;base64,${base64Data}`).then(res => res.blob());
        
        // Create a timestamp for unique filename
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const fileName = `photo_${timestamp}.jpg`;
        
        // Create a download link and trigger it
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = fileName;
        a.style.display = 'none';
        
        // Set the download attribute to include the folder path
        a.setAttribute('download', `accounts/${folderName}/${fileName}`);
        
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(a.href);
        
        return fileName;
    } catch (err) {
        console.error('Error saving image:', err);
        throw err;
    }
}

// Event Listeners
tiles.forEach(tile => {
    tile.addEventListener('click', async () => {
        currentSymbol = tile.dataset.symbol;
        modal.style.display = 'block';
        await getCameraDevices();
        await initializeCamera();
    });
});

// Handle camera selection change
cameraSelect.addEventListener('change', () => {
    initializeCamera();
});

closeButton.addEventListener('click', () => {
    modal.style.display = 'none';
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
    }
});

captureButton.addEventListener('click', async () => {
    try {
        // Set canvas dimensions to match video
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        
        // Draw the current video frame on the canvas
        const context = canvas.getContext('2d');
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        // Convert the canvas to a data URL
        const imageData = canvas.toDataURL('image/jpeg', 0.8);
        
        // Get the folder name for the current symbol
        const folderName = symbolToFolder[currentSymbol];
        if (!folderName) {
            throw new Error('Invalid symbol selected');
        }
        
        // Save the image to the corresponding folder
        const fileName = await saveImage(imageData, folderName);
        
        // Close the modal and stop the camera
        modal.style.display = 'none';
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
        }
        
        // Show success message with the file location
        alert(`Picture saved as ${fileName} in the ${folderName} folder!`);
    } catch (err) {
        console.error('Error capturing image:', err);
        alert('Failed to save the image. Please try again.');
    }
});

// Close modal when clicking outside
window.addEventListener('click', (event) => {
    if (event.target === modal) {
        modal.style.display = 'none';
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
        }
    }
}); 