// DOM Elements
const symbolSelection = document.getElementById('symbolSelection');
const contentDisplay = document.getElementById('contentDisplay');
const backButton = document.getElementById('backButton');
const selectedSymbol = document.getElementById('selectedSymbol');
const imageGallery = document.getElementById('imageGallery');



// Image view modal elements
const imageViewModal = document.getElementById('imageViewModal');
const enlargedImage = document.getElementById('enlargedImage');
const imageFileName = document.getElementById('imageFileName');
const imageCloseButton = document.querySelector('.image-close-button');

const tiles = document.querySelectorAll('.tile');

// State variables
let currentSymbol = '';
let currentFolder = '';
let imageDescriptions = {};
let selectedDirection = '';

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

// Load images from the accounts folder
async function loadImagesFromFolder(folderName) {
    try {
        const response = await fetch(`/list-images/${folderName}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        return data.images || [];
    } catch (error) {
        console.error('Error loading images:', error);
        return [];
    }
}

// Display images in the gallery
function displayImages(images, folderName) {
    imageGallery.innerHTML = '';
    
    if (images.length === 0) {
        imageGallery.innerHTML = '<p class="no-images-message">Noch keine Fotos vorhanden. Nimm ein paar Fotos auf, um sie hier zu sehen!</p>';
        return;
    }
    
    images.forEach(imageName => {
        const imageContainer = document.createElement('div');
        imageContainer.className = 'image-container';
        
        const img = document.createElement('img');
        // Properly encode the image name for URLs
        const encodedImageName = encodeURIComponent(imageName);
        img.src = `/accounts/${folderName}/${encodedImageName}`;
        img.alt = imageName;
        img.className = 'gallery-image';
        img.onerror = function() {
            console.error('Failed to load image:', this.src);
            this.style.display = 'none';
        };
        
        // Add click event to open image in modal
        img.addEventListener('click', () => {
            openImageView(img.src, imageName);
        });
        
        // Create description section
        const descriptionSection = document.createElement('div');
        descriptionSection.className = 'image-description-section';
        
        // Create use image checkbox
        const useImageSection = document.createElement('div');
        useImageSection.className = 'use-image-section';
        
        const useImageCheckbox = document.createElement('input');
        useImageCheckbox.type = 'checkbox';
        useImageCheckbox.className = 'use-image-checkbox';
        useImageCheckbox.dataset.imageName = imageName;
        useImageCheckbox.id = `use-image-${imageName.replace(/[^a-zA-Z0-9]/g, '-')}`;
        
        const useImageLabel = document.createElement('label');
        useImageLabel.className = 'use-image-label';
        useImageLabel.textContent = 'Bild verwenden';
        useImageLabel.htmlFor = useImageCheckbox.id;
        
        // Load existing use image selection
        const existingUseImage = imageDescriptions[imageName]?.useImage || false;
        useImageCheckbox.checked = existingUseImage === true || existingUseImage === 'true';
        
        useImageSection.appendChild(useImageCheckbox);
        useImageSection.appendChild(useImageLabel);
        
        // Create description field
        const label = document.createElement('label');
        label.className = 'description-label';
        label.textContent = 'Bildbeschreibung oder Erzählung:';
        
        const textarea = document.createElement('textarea');
        textarea.className = 'image-description';
        textarea.placeholder = 'Beschreibe das Bild oder erzähle den Teil der Geschichte der zu diesem Bild gehört...';
        textarea.dataset.imageName = imageName;
        
        // Load existing description
        const existingDescription = imageDescriptions[imageName]?.description || '';
        console.log(`Setting description for ${imageName}:`, existingDescription);
        textarea.value = existingDescription;
        
        descriptionSection.appendChild(useImageSection);
        descriptionSection.appendChild(label);
        descriptionSection.appendChild(textarea);
        
        imageContainer.appendChild(img);
        imageContainer.appendChild(descriptionSection);
        imageGallery.appendChild(imageContainer);
    });
}

// Load image descriptions from server
async function loadImageDescriptions(folderName) {
    try {
        console.log('Loading descriptions for folder:', folderName);
        const response = await fetch(`/load-descriptions/${folderName}`);
        console.log('Response status:', response.status);
        
        if (response.ok) {
            const data = await response.json();
            console.log('Loaded descriptions:', data);
            imageDescriptions = data.descriptions || {};
            console.log('Image descriptions object:', imageDescriptions);
        } else {
            console.error('Failed to load descriptions, status:', response.status);
            imageDescriptions = {};
        }
    } catch (error) {
        console.error('Error loading descriptions:', error);
        imageDescriptions = {};
    }
}

// Save image description to server
async function saveImageDescription(folderName, imageName, description) {
    try {
        const response = await fetch('/save-description', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                folder: folderName,
                imageName: imageName,
                description: description
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            if (result.success) {
                imageDescriptions[imageName] = description;
                return true;
            }
        }
        return false;
    } catch (error) {
        console.error('Error saving description:', error);
        return false;
    }
}

// Open image view modal
function openImageView(imageSrc, fileName) {
    enlargedImage.src = imageSrc;
    imageFileName.textContent = fileName;
    imageViewModal.style.display = 'block';
}

// Close image view modal
function closeImageView() {
    imageViewModal.style.display = 'none';
    enlargedImage.src = '';
    imageFileName.textContent = '';
}

// Create default content for symbols
function createDefaultContent(symbol) {
    const symbolNames = {
        '🌟': 'Star', '🌈': 'Rainbow', '🌺': 'Flower', '🦋': 'Butterfly',
        '🐬': 'Dolphin', '🦁': 'Lion', '🐘': 'Elephant', '🦒': 'Giraffe',
        '🦊': 'Fox', '🐼': 'Panda', '🐢': 'Turtle', '🦉': 'Owl',
        '🦄': 'Unicorn', '🐠': 'Fish', '🦚': 'Peacock'
    };

    return {
        symbol: symbol
    };
}

// Display content for selected symbol
async function displayContent(symbol) {
    const folderName = symbolToFolder[symbol];
    if (!folderName) {
        console.error('Invalid symbol:', symbol);
        return;
    }
    
    currentSymbol = symbol;
    currentFolder = folderName;
    
    // Create default content
    const content = createDefaultContent(symbol);
    
    // Update UI elements
    selectedSymbol.textContent = content.symbol;
    
    // Load image descriptions first
    await loadImageDescriptions(folderName);
    
    // Load and display images
    const images = await loadImagesFromFolder(folderName);
    displayImages(images, folderName);
    
    // Show content display
    symbolSelection.style.display = 'none';
    contentDisplay.style.display = 'block';
    
    // Initialize direction buttons
    initializeDirectionButtons();
}

// Handle story direction selection
function handleDirectionSelection(direction) {
    // Remove selected class from all buttons
    document.querySelectorAll('.direction-btn').forEach(btn => {
        btn.classList.remove('selected');
    });
    
    // Add selected class to clicked button
    const clickedBtn = document.querySelector(`[data-direction="${direction}"]`);
    if (clickedBtn) {
        clickedBtn.classList.add('selected');
    }
    
    selectedDirection = direction;
    
    // Show/hide custom input
    const customInput = document.getElementById('customDirectionInput');
    if (direction === 'custom') {
        customInput.style.display = 'block';
    } else {
        customInput.style.display = 'none';
    }
}

// Initialize direction buttons
function initializeDirectionButtons() {
    const directionButtons = document.querySelectorAll('.direction-btn');
    directionButtons.forEach(button => {
        button.addEventListener('click', () => {
            const direction = button.dataset.direction;
            handleDirectionSelection(direction);
        });
    });
}

// Reset to initial state
function resetToInitialState() {
    // Reset form fields
    const storyTitleInput = document.getElementById('storyTitle');
    const customDirectionText = document.getElementById('customDirectionText');
    
    if (storyTitleInput) storyTitleInput.value = '';
    if (customDirectionText) customDirectionText.value = '';
    
    // Reset direction selection
    selectedDirection = '';
    document.querySelectorAll('.direction-btn').forEach(btn => {
        btn.classList.remove('selected');
    });
    
    // Hide custom direction input
    const customInput = document.getElementById('customDirectionInput');
    if (customInput) customInput.style.display = 'none';
    
    // Reset image descriptions
    imageDescriptions = {};
    
    // Clear image gallery
    if (imageGallery) imageGallery.innerHTML = '';
    
    // Reset button state
    const sendAllBtn = document.getElementById('sendAllInfo');
    if (sendAllBtn) {
        sendAllBtn.textContent = 'Generiere deine Geschichte';
        sendAllBtn.disabled = false;
    }
    
    // Show symbol selection, hide content display
    symbolSelection.style.display = 'block';
    contentDisplay.style.display = 'none';
    
    // Reset state variables
    currentSymbol = '';
    currentFolder = '';
    
    console.log('Reset to initial state completed');
}

// Send all information function
async function sendAllInformation() {
    const sendAllBtn = document.getElementById('sendAllInfo');
    const storyTitleInput = document.getElementById('storyTitle');
    const textareas = document.querySelectorAll('.image-description');
    const selects = document.querySelectorAll('.use-image-select');
    
    // Validation checks
    const title = storyTitleInput.value.trim();
    if (!title) {
        alert('Bitte gib deiner Geschichte einen Titel!');
        storyTitleInput.focus();
        return;
    }
    
    if (!selectedDirection) {
        alert('Bitte wähle eine Richtung für deine Geschichte aus!');
        return;
    }
    
    if (selectedDirection === 'custom') {
        const customText = document.getElementById('customDirectionText').value.trim();
        if (!customText) {
            alert('Bitte beschreibe deine eigene Geschichte!');
            document.getElementById('customDirectionText').focus();
            return;
        }
    }
    
    // Count selected images
    let selectedImageCount = 0;
    const selectedImages = {};
    
    textareas.forEach(textarea => {
        const imageName = textarea.dataset.imageName;
        const description = textarea.value.trim();
        const useImageCheckbox = document.querySelector(`.use-image-checkbox[data-image-name="${imageName}"]`);
        const useImage = useImageCheckbox ? useImageCheckbox.checked : false;
        
        if (imageName) {
            if (useImage) {
                selectedImageCount++;
                selectedImages[imageName] = {
                    description: description,
                    useImage: useImage
                };
            }
        }
    });
    
    if (selectedImageCount === 0) {
        alert('Bitte wähle mindestens ein Bild aus!');
        return;
    }
    
    if (selectedImageCount > 4) {
        alert('Du kannst maximal 4 Bilder auswählen! Du hast ' + selectedImageCount + ' Bilder ausgewählt.');
        return;
    }
    
    // Collect all descriptions and use image selections
    const allData = {
        symbol: currentSymbol,
        folder: currentFolder,
        title: title,
        direction: selectedDirection,
        customDirection: selectedDirection === 'custom' ? document.getElementById('customDirectionText').value.trim() : '',
        descriptions: {}
    };
    
    textareas.forEach(textarea => {
        const imageName = textarea.dataset.imageName;
        const description = textarea.value.trim();
        const useImageCheckbox = document.querySelector(`.use-image-checkbox[data-image-name="${imageName}"]`);
        const useImage = useImageCheckbox ? useImageCheckbox.checked : false;
        
        if (imageName) {
            allData.descriptions[imageName] = {
                description: description,
                useImage: useImage
            };
        }
    });
    
    // Reset UI immediately and send data in background
    resetToInitialState();
    
    // Send data to server in background (non-blocking)
    fetch('/send-all-info', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(allData)
    })
    .then(response => {
        if (response.ok) {
            return response.json();
        } else {
            throw new Error('Network response was not ok');
        }
    })
    .then(result => {
        if (result.success) {
            console.log('Story generation started successfully');
        } else {
            console.error('Failed to start story generation');
        }
    })
    .catch(error => {
        console.error('Error sending information:', error);
    });
}

// Event Listeners
tiles.forEach(tile => {
    tile.addEventListener('click', async () => {
        const symbol = tile.dataset.symbol;
        await displayContent(symbol);
    });
});

// Back button event listener
backButton.addEventListener('click', () => {
    contentDisplay.style.display = 'none';
    symbolSelection.style.display = 'block';
    currentSymbol = '';
    currentFolder = '';
});

// Send all information button event listener
document.addEventListener('DOMContentLoaded', () => {
    const sendAllBtn = document.getElementById('sendAllInfo');
    if (sendAllBtn) {
        sendAllBtn.addEventListener('click', sendAllInformation);
    }
});

// Close image view modal when clicking outside
window.addEventListener('click', (event) => {
    // Close image view modal when clicking outside
    if (event.target === imageViewModal) {
        closeImageView();
    }
});

// Image view modal event listeners
imageCloseButton.addEventListener('click', closeImageView);

// Close image view modal with Escape key
document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
        if (imageViewModal.style.display === 'block') {
            closeImageView();
        }
    }
}); 