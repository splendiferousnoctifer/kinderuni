import json
import os

# Define the emoji mappings
folder_to_emoji = {
    'star': '🌟',
    'rainbow': '🌈',
    'flower': '🌺',
    'butterfly': '🦋',
    'dolphin': '🐬',
    'lion': '🦁',
    'elephant': '🐘',
    'giraffe': '🦒',
    'fox': '🦊',
    'panda': '🐼',
    'turtle': '🐢',
    'owl': '🦉',
    'unicorn': '🦄',
    'fish': '🐠',
    'peacock': '🦚'
}

# Create JSON files in each folder
for folder_name, emoji in folder_to_emoji.items():
    folder_path = os.path.join('accounts', folder_name)
    
    # Ensure the folder exists
    os.makedirs(folder_path, exist_ok=True)
    
    # Create the JSON data
    data = {
        'folder_name': folder_name,
        'emoji': emoji,
        'description': f'Account folder for {folder_name} symbol ({emoji})'
    }
    
    # Write the JSON file
    json_path = os.path.join(folder_path, f'{folder_name}.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

print("JSON files created successfully!") 