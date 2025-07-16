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

// Ensure console.log works
if (!console.log) {
    console.log = function() {};
}

// Force log to both console and DOM
function forceLog(message, data = null) {
    const timestamp = new Date().toISOString();
    const logDiv = document.createElement('div');
    logDiv.style.position = 'fixed';
    logDiv.style.top = '0';
    logDiv.style.left = '0';
    logDiv.style.backgroundColor = 'rgba(0,0,0,0.8)';
    logDiv.style.color = 'white';
    logDiv.style.padding = '5px';
    logDiv.style.zIndex = '9999';
    logDiv.style.maxWidth = '100%';
    logDiv.style.wordBreak = 'break-all';
    
    let logMessage = `[${timestamp}] ${message}`;
    if (data) {
        logMessage += ': ' + JSON.stringify(data);
    }
    
    logDiv.textContent = logMessage;
    document.body.appendChild(logDiv);
    
    // Remove after 5 seconds
    setTimeout(() => logDiv.remove(), 5000);
    
    // Also log to console if available
    console.log(logMessage);
}

// Apply mirror effect to video
video.style.transform = 'scaleX(-1)';

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
        console.log('Starting camera device enumeration...');
        
        // First, clear any existing streams
        if (stream) {
            stream.getTracks().forEach(track => {
                track.stop();
                stream.removeTrack(track);
            });
            stream = null;
        }
        
        // Force permission prompt by requesting with exact constraints
        try {
            const testStream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { exact: 1280 },
                    height: { exact: 720 }
                }
            });
            testStream.getTracks().forEach(track => track.stop());
        } catch (err) {
            console.log('Forcing permission prompt:', err);
            // Expected to fail sometimes, we just want to trigger the prompt
        }
        
        // Now enumerate devices
        await navigator.mediaDevices.getUserMedia({ video: true });
        const devices = await navigator.mediaDevices.enumerateDevices();
        console.log('All devices found:', devices);
        
        const videoDevices = devices.filter(device => device.kind === 'videoinput');
        console.log('Video devices found:', videoDevices);
        
        // Clear existing options
        cameraSelect.innerHTML = '';
        
        // Find IPEVO camera first
        let selectedDevice = null;
        for (let device of videoDevices) {
            const deviceInfo = (device.label || '').toLowerCase();
            const groupInfo = (device.groupId || '').toLowerCase();
            
            console.log('Checking device for IPEVO:', {
                label: deviceInfo,
                groupId: groupInfo,
                deviceId: device.deviceId
            });
            
            if (deviceInfo.includes('ipevo') || 
                deviceInfo.includes('1778:d002') || 
                groupInfo.includes('1778:d002')) {
                console.log('Found IPEVO camera! Using it as default:', device);
                selectedDevice = device;
                break;
            }
        }
        
        // Add options and select IPEVO if found
        videoDevices.forEach((device, index) => {
            const option = document.createElement('option');
            option.value = device.deviceId;
            option.text = device.label || `Camera ${index + 1}`;
            
            // Mark IPEVO as standard
            if (device === selectedDevice) {
                option.text += ' (Standard)';
                option.selected = true;
            }
            
            cameraSelect.appendChild(option);
        });

        // Initialize with selected device if found, otherwise use default
        if (selectedDevice) {
            console.log('Initializing with IPEVO camera');
            await initializeCamera(selectedDevice.deviceId);
        } else {
            console.log('IPEVO camera not found, using default camera');
            await initializeCamera();
        }
    } catch (err) {
        console.error('Error getting camera devices:', err);
    }
}

// Initialize camera access
async function initializeCamera(deviceId = null) {
    try {
        forceLog('Initializing camera', { deviceId });
        
        // Stop any existing stream
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            forceLog('Stopped existing camera stream');
        }
        
        const constraints = {
            video: {
                deviceId: deviceId ? { exact: deviceId } : undefined,
                width: { ideal: 1280 },
                height: { ideal: 720 }
            }
        };
        forceLog('Using camera constraints', constraints);
        
        stream = await navigator.mediaDevices.getUserMedia(constraints);
        video.srcObject = stream;
        forceLog('Camera initialized successfully');
        
        // Wait for video to be ready
        await new Promise((resolve) => {
            video.onloadedmetadata = () => {
                forceLog('Video metadata loaded');
                resolve();
            };
        });
        
        forceLog('Camera setup complete');
    } catch (err) {
        forceLog('Error accessing camera', err);
        alert('Unable to access camera. Please make sure you have granted camera permissions.');
    }
}

// Save image to server
async function saveImage(imageData, folderName) {
    try {
        const response = await fetch('/save-image', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                imageData: imageData,
                folder: folderName
            })
        });

        if (!response.ok) {
            throw new Error('Failed to save image');
        }

        const result = await response.json();
        return result.filename;
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
    });
});

// Handle camera selection change
cameraSelect.addEventListener('change', (event) => {
    forceLog('Camera selection changed', { newDeviceId: event.target.value });
    initializeCamera(event.target.value);
});

closeButton.addEventListener('click', () => {
    modal.style.display = 'none';
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        forceLog('Camera stream stopped');
    }
});

captureButton.addEventListener('click', async () => {
    try {
        // Set canvas dimensions to match video
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        
        // Draw the current video frame on the canvas
        const context = canvas.getContext('2d');
        
        // Apply the same mirror effect when capturing
        context.scale(-1, 1);
        context.translate(-canvas.width, 0);
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        // Reset transformation
        context.setTransform(1, 0, 0, 1, 0, 0);
        
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
        alert(`Foto wurde als ${fileName} im Ordner ${folderName} gespeichert!`);
    } catch (err) {
        console.error('Error capturing image:', err);
        alert('Fehler beim Speichern des Fotos. Bitte versuchen Sie es erneut.');
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