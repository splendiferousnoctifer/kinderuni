from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os
import base64
from datetime import datetime
from urllib.parse import parse_qs, urlparse, unquote
import threading
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import shutil
import glob
from google import genai
import posixpath
import urllib.parse

# Configure Gemini API
def configure_gemini():
    """Configure the Gemini API with your API key"""
    # You'll need to set your API key as an environment variable
    # export GOOGLE_API_KEY="your-api-key-here"
    api_key = "AIzaSyBHkEw47Dk-bZwKui1Rm4Zn833M-vmySsE"
    if not api_key:
        print("Warning: GOOGLE_API_KEY environment variable not set")
        return None
    return genai.Client(api_key=api_key)

def send_to_genai(story_prompt_file):
    """
    Send story information to Gemini 2.5 Flash for story generation
    """
    try:
        # Load the story prompt data
        with open(story_prompt_file, 'r', encoding='utf-8') as f:
            story_data = json.load(f)
        
        print(f"Processing story for {story_data['symbol']} ({story_data['folder']})")
        
        # Initialize Gemini model
        client = configure_gemini()
        if not client:
            print("Gemini not configured, skipping story generation")
            return
        
        # Prepare the prompt for Gemini
        prompt = create_story_prompt(story_data)
        
        # Upload and prepare images
        contents = [prompt]
        folder_path = os.path.join('accounts', story_data['folder'])
        
        for image_name in story_data['selected_images'].keys():
            image_path = os.path.join(folder_path, image_name)
            
            if os.path.exists(image_path):
                try:
                    # Upload image to Gemini
                    uploaded_file = client.files.upload(file=image_path)
                    contents.append(uploaded_file)
                    print(f"Uploaded image: {image_name}")
                except Exception as e:
                    print(f"Error uploading image {image_name}: {str(e)}")
                    # Continue with other images even if one fails
            else:
                print(f"Image not found: {image_path}")
        
        # Send to Gemini with images
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=contents
        )
        
        if response.text:
            # Parse the JSON response from Gemini
            try:
                # Clean the response text - remove any markdown formatting
                cleaned_response = response.text.strip()
                
                # Remove markdown code blocks if present
                if cleaned_response.startswith('```json'):
                    cleaned_response = cleaned_response[7:]
                if cleaned_response.startswith('```'):
                    cleaned_response = cleaned_response[3:]
                if cleaned_response.endswith('```'):
                    cleaned_response = cleaned_response[:-3]
                
                cleaned_response = cleaned_response.strip()
                
                print(f"Cleaned response: {cleaned_response[:200]}...")
                
                story_content = json.loads(cleaned_response)
                save_generated_story(story_data, story_content, story_prompt_file)
                print(f"Story generated successfully for {story_data['symbol']}")
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON response from Gemini: {str(e)}")
                print(f"Raw response: {response.text}")
                print(f"Cleaned response: {cleaned_response}")
                # Save as plain text if JSON parsing fails
                save_generated_story(story_data, response.text, story_prompt_file)
        else:
            print("No response from Gemini")
            
    except Exception as e:
        print(f"Error sending to Gemini: {str(e)}")

def create_story_prompt(story_data):
    """
    Create a structured prompt for Gemini based on the story data
    """
    title = story_data['title']
    direction = story_data['direction']
    custom_direction = story_data['custom_direction']
    selected_images = story_data['selected_images']
    
    # Build the prompt
    prompt = f"""
Du bist ein kreativer Geschichtenerzähler für Kinder. Erstelle eine spannende, kindgerechte Geschichte basierend auf den folgenden Informationen:

TITEL: {title}

GESCHICHTENRICHTUNG: {direction}
"""
    
    if direction == 'custom' and custom_direction:
        prompt += f"BESCHREIBUNG DER EIGENEN IDEE: {custom_direction}\n"
    elif direction == 'pirates':
        prompt += "Die Geschichte soll Piraten und Abenteuer auf hoher See beinhalten.\n"
    elif direction == 'fairies':
        prompt += "Die Geschichte soll Feen und magische Wesen beinhalten.\n"
    elif direction == 'dragon':
        prompt += "Die Geschichte soll einen Drachen und magische Abenteuer beinhalten.\n"
    
    prompt += f"\nBILDBESCHREIBUNGEN (zusätzlich zu den hochgeladenen Bildern):\n"
    
    for image_name, image_data in selected_images.items():
        description = image_data.get('description', '')
        if description:
            prompt += f"- {image_name}: {description}\n"
    
    prompt += f"""
ANWEISUNGEN:
- Schreibe eine Geschichte für Kinder im Alter von 6-10 Jahren
- Verwende einfache, verständliche Sprache
- Mache die Geschichte spannend und unterhaltsam
- Betrachte alle hochgeladenen Bilder genau und integriere sie in die Geschichte
- Berücksichtige auch die zusätzlichen Beschreibungen der Bilder
- Die Geschichte sollte etwa 300-500 Wörter lang sein
- Verwende den gegebenen Titel als Titel der Geschichte
- Erzähle die Geschichte so, als würdest du sie einem Kind vorlesen
- Die Geschichte sollte in 4 Absätzen sein wobei jeder Absatz etwa 100 Wörter lang ist
- Jedem der mitgegebenen Bild soll ein Absatz zugeordnet werden, wenn weniger als 4 Bilder mitgegeben werden, dann können die restlichen Absätze frei mit Text gefüllt werden
- Wenn weniger als 4 Bilder mitgegeben werden, erstelle für die Absätze ohne Bild einen Prompt in der image_description, mit welchem ein zum Absatz passendes Bild generiert werden kann

Schreibe die Geschichte in Deutsch und formatiere sie schön mit 4 Absätzen. 

WICHTIG: Gib NUR das JSON-Objekt zurück, ohne Markdown-Formatierung oder Code-Blöcke. Verwende dieses exakte Format:

{{
    "titel": "Titel der Geschichte",
    "absatz1": {{
        "text": "Der erste Absatz der Geschichte",
        "image": "Bildname oder null",
        "image_description": "Beschreibung des Bildes oder Prompt um das Bild zu generieren"
    }},
    "absatz2": {{
        "text": "Der zweite Absatz der Geschichte", 
        "image": "Bildname oder null",
        "image_description": "Beschreibung des Bildes oder Prompt um das Bild zu generieren"
    }},
    "absatz3": {{
        "text": "Der dritte Absatz der Geschichte",
        "image": "Bildname oder null",
        "image_description": "Beschreibung des Bildes oder Prompt um das Bild zu generieren"
    }},
    "absatz4": {{
        "text": "Der vierte Absatz der Geschichte",
        "image": "Bildname oder null",
        "image_description": "Beschreibung des Bildes oder Prompt um das Bild zu generieren"
    }}
}}

Antworte NUR mit dem JSON-Objekt, nichts anderes.
"""
    
    return prompt

def save_generated_story(story_data, story_content, original_file_path):
    """
    Save the generated story back to the same folder
    """
    try:
        folder_path = os.path.dirname(original_file_path)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create story file with generated content
        story_file = os.path.join(folder_path, f'generated_story_{timestamp}.json')
        
        # Check if story_content is already a dict (parsed JSON) or a string
        if isinstance(story_content, dict):
            # Structured JSON content
            story_output = {
                'symbol': story_data['symbol'],
                'folder': story_data['folder'],
                'title': story_data['title'],
                'direction': story_data['direction'],
                'custom_direction': story_data['custom_direction'],
                'timestamp': datetime.now().isoformat(),
                'selected_images': story_data['selected_images'],
                'story': story_content,  # This is now the structured JSON
                'original_prompt_file': os.path.basename(original_file_path)
            }
        else:
            # Plain text content (fallback)
            story_output = {
                'symbol': story_data['symbol'],
                'folder': story_data['folder'],
                'title': story_data['title'],
                'direction': story_data['direction'],
                'custom_direction': story_data['custom_direction'],
                'timestamp': datetime.now().isoformat(),
                'selected_images': story_data['selected_images'],
                'content': story_content,  # Plain text fallback
                'original_prompt_file': os.path.basename(original_file_path)
            }
        
        with open(story_file, 'w', encoding='utf-8') as f:
            json.dump(story_output, f, ensure_ascii=False, indent=2)
        
        print(f"Generated story saved to: {story_file}")
        
    except Exception as e:
        print(f"Error saving generated story: {str(e)}")

class AccountsHandler(FileSystemEventHandler):
    def __init__(self):
        self.emoji_map = self._load_emoji_map()

    def _load_emoji_map(self):
        emoji_map = {}
        accounts_path = 'accounts'
        for folder in os.listdir(accounts_path):
            folder_path = os.path.join(accounts_path, folder)
            if os.path.isdir(folder_path):
                json_file = os.path.join(folder_path, f'{folder}.json')
                if os.path.exists(json_file):
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        emoji_map[folder] = data.get('emoji', '📚')
        return emoji_map

    def on_created(self, event):
        if event.is_directory or not event.src_path.endswith('.json'):
            return
            
        file_path = event.src_path
        folder_name = os.path.basename(os.path.dirname(file_path))
        file_name = os.path.basename(file_path)
        
        # Skip folder definition files and files that don't start with generated_story
        if file_name == f'{folder_name}.json' or not file_name.startswith('generated_story'):
            return
            
        try:
            # Wait a brief moment to ensure file is fully written
            time.sleep(0.1)
            
            # Read and process the JSON file
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Check for story section
            if 'story' in data:
                print(f"New story detected: {file_path}")
            else:
                print(f"No story section found in {file_path}")
                
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")

class CustomHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.debug = True  # Set to True to enable debug logging
        super().__init__(*args, **kwargs)

    def log_debug(self, message):
        if self.debug:
            print(f"[DEBUG] {message}")

    def find_file_in_stations(self, request_path):
        """Find the correct file path in station directories"""
        # Remove leading slash and normalize path
        path = request_path.lstrip('/')
        if not path or path.endswith('/'):
            path = path + 'index.html'
        
        self.log_debug(f"Looking for file: {path}")
        
        # If path starts with station_, look in that station first
        parts = path.split('/', 1)
        if len(parts) > 1 and parts[0].startswith('station_'):
            station = parts[0]
            subpath = parts[1]
            station_path = os.path.join(station, subpath)
            if os.path.exists(station_path):
                self.log_debug(f"Found in specified station: {station_path}")
                return f"/{station_path}"
        
        # Check each station directory
        for station in ['station_1', 'station_2', 'station_3']:
            station_path = os.path.join(station, path)
            if os.path.exists(station_path):
                self.log_debug(f"Found in station directory: {station_path}")
                return f"/{station_path}"
            
        # If not found in stations, try direct path
        if os.path.exists(path):
            self.log_debug(f"Found in root: {path}")
            return f"/{path}"
            
        self.log_debug(f"File not found: {path}")
        return None

    def do_GET(self):
        # Special endpoints handling first
        if self.path.rstrip('/') == '/get-stories':
            self.handle_get_stories()
            return
        elif self.path.startswith('/list-images/'):
            self.handle_list_images()
            return
        elif self.path.startswith('/load-descriptions/'):
            self.handle_load_descriptions()
            return
        elif self.path.startswith('/accounts/'):
            self.handle_accounts_file()
            return
        elif self.path.rstrip('/') == '/timer-expired':
            self.handle_timer_expired()
            return
            
        # Handle static file serving
        file_path = self.find_file_in_stations(self.path)
        if file_path:
            self.log_debug(f"Serving file: {file_path}")
            self.path = file_path
            return SimpleHTTPRequestHandler.do_GET(self)
        else:
            self.log_debug(f"No file found for path: {self.path}")
            self.send_error(404, "File not found")
            return

    def do_POST(self):
        if self.path == '/save-image':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            image_data = data['imageData']
            folder = data['folder']
            
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            
            timestamp = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
            filename = f'photo_{timestamp}.jpg'
            
            folder_path = os.path.join('accounts', folder)
            os.makedirs(folder_path, exist_ok=True)
            
            file_path = os.path.join(folder_path, filename)
            with open(file_path, 'wb') as f:
                f.write(base64.b64decode(image_data))
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = json.dumps({'success': True, 'filename': filename})
            self.wfile.write(response.encode())
        
        elif self.path == '/save-description':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            folder = data['folder']
            image_name = data['imageName']
            description = data['description']
            
            folder_path = os.path.join('accounts', folder)
            descriptions_file = os.path.join(folder_path, 'descriptions.json')
            
            try:
                # Load existing descriptions
                descriptions = {}
                if os.path.exists(descriptions_file):
                    with open(descriptions_file, 'r', encoding='utf-8') as f:
                        descriptions = json.load(f)
                
                # Update or add the description (handle both old and new format)
                if isinstance(description, dict):
                    # New format with description and useImage
                    descriptions[image_name] = description
                else:
                    # Old format - just description string
                    descriptions[image_name] = {
                        'description': description,
                        'useImage': False
                    }
                
                # Save back to file
                with open(descriptions_file, 'w', encoding='utf-8') as f:
                    json.dump(descriptions, f, ensure_ascii=False, indent=2)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = json.dumps({'success': True})
                self.wfile.write(response.encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = json.dumps({'error': str(e)})
                self.wfile.write(response.encode())
        
        elif self.path == '/send-all-info':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            symbol = data['symbol']
            folder = data['folder']
            title = data.get('title', '')
            direction = data.get('direction', '')
            custom_direction = data.get('customDirection', '')
            descriptions = data['descriptions']
            
            folder_path = os.path.join('accounts', folder)
            descriptions_file = os.path.join(folder_path, 'descriptions.json')
            
            try:
                # Save all descriptions to file
                with open(descriptions_file, 'w', encoding='utf-8') as f:
                    json.dump(descriptions, f, ensure_ascii=False, indent=2)
                
                # Create story prompt context file with timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                story_prompt_file = os.path.join(folder_path, f'story_prompt_kontext_{timestamp}.json')
                
                # Filter only selected images (useImage = true)
                selected_images = {}
                for image_name, image_data in descriptions.items():
                    if isinstance(image_data, dict) and image_data.get('useImage', False):
                        selected_images[image_name] = image_data
                
                story_data = {
                    'symbol': symbol,
                    'folder': folder,
                    'title': title,
                    'direction': direction,
                    'custom_direction': custom_direction,
                    'timestamp': datetime.now().isoformat(),
                    'selected_images': selected_images,
                    'total_selected_images': len(selected_images)
                }
                
                with open(story_prompt_file, 'w', encoding='utf-8') as f:
                    json.dump(story_data, f, ensure_ascii=False, indent=2)
                
                print(f"Saved story prompt context for {symbol} ({folder}): {len(selected_images)} selected images")
                print(f"Story file: {story_prompt_file}")

                send_to_genai(story_prompt_file)
                print("Sent to genai")
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = json.dumps({
                    'success': True, 
                    'message': f'Saved story with {len(selected_images)} selected images',
                    'filename': f'story_prompt_kontext_{timestamp}.json'
                })
                self.wfile.write(response.encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = json.dumps({'error': str(e)})
                self.wfile.write(response.encode())
        
        else:
            return SimpleHTTPRequestHandler.do_POST(self)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        SimpleHTTPRequestHandler.end_headers(self)

    def handle_get_stories(self):
        try:
            stories = []
            accounts_path = 'accounts'
            
            # Load emoji map
            emoji_map = {}
            for folder in os.listdir(accounts_path):
                folder_path = os.path.join(accounts_path, folder)
                if os.path.isdir(folder_path):
                    json_file = os.path.join(folder_path, f'{folder}.json')
                    if os.path.exists(json_file):
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            emoji_map[folder] = data.get('emoji', '📚')
            
            # Find all story JSON files
            for folder in os.listdir(accounts_path):
                folder_path = os.path.join(accounts_path, folder)
                if os.path.isdir(folder_path):
                    for file in os.listdir(folder_path):
                        if file.startswith('generated_story') and file.endswith('.json'):
                            file_path = os.path.join(folder_path, file)
                            with open(file_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                if 'story' in data:
                                    content = {}
                                    story = data['story']
                                    for i, (key, section) in enumerate(story.items(), 1):
                                        if isinstance(section, dict) and 'text' in section:
                                            content[f'text_{i}'] = section['text']
                                            if section.get('image'):
                                                content[f'img_{i}'] = os.path.join(folder, section['image'])
                                    
                                    story = {
                                        'id': os.path.splitext(file)[0],
                                        'emoji': emoji_map.get(folder, '📚'),
                                        'title': data.get('title', story.get('titel', 'Neue Geschichte')),
                                        'content': content
                                    }
                                    stories.append(story)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(stories).encode())
        except Exception as e:
            self.log_debug(f"Error getting stories: {str(e)}")
            self.send_error(500, str(e))

    def handle_list_images(self):
        folder_name = self.path.split('/list-images/')[1]
        folder_path = os.path.join('accounts', folder_name)
        
        try:
            image_files = []
            if os.path.exists(folder_path):
                for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif']:
                    pattern = os.path.join(folder_path, ext)
                    files = glob.glob(pattern)
                    for file in files:
                        image_files.append(os.path.basename(file))
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = json.dumps({'images': image_files})
            self.wfile.write(response.encode())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = json.dumps({'error': str(e)})
            self.wfile.write(response.encode())

    def handle_load_descriptions(self):
        folder_name = self.path.split('/load-descriptions/')[1]
        descriptions_file = os.path.join('accounts', folder_name, 'descriptions.json')
        
        try:
            descriptions = {}
            if os.path.exists(descriptions_file):
                with open(descriptions_file, 'r', encoding='utf-8') as f:
                    descriptions = json.load(f)
                
                # Handle backward compatibility
                for image_name, description_data in descriptions.items():
                    if isinstance(description_data, str):
                        descriptions[image_name] = {
                            'description': description_data,
                            'useImage': False
                        }
                    elif isinstance(description_data, dict) and 'useImage' in description_data:
                        if isinstance(description_data['useImage'], str):
                            descriptions[image_name]['useImage'] = description_data['useImage'].lower() in ['true', 'yes', '1']
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = json.dumps({'descriptions': descriptions})
            self.wfile.write(response.encode())
        except Exception as e:
            self.log_debug(f"Error loading descriptions: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = json.dumps({'error': str(e)})
            self.wfile.write(response.encode())

    def handle_accounts_file(self):
        file_path = unquote(self.path)
        file_path = '.' + file_path
        
        if os.path.exists(file_path) and os.path.isfile(file_path):
            self.send_response(200)
            if file_path.endswith(('.jpg', '.jpeg')):
                self.send_header('Content-type', 'image/jpeg')
            elif file_path.endswith('.png'):
                self.send_header('Content-type', 'image/png')
            elif file_path.endswith('.gif'):
                self.send_header('Content-type', 'image/gif')
            else:
                self.send_header('Content-type', 'application/octet-stream')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'File not found')

    def handle_timer_expired(self):
        try:
            files_to_move = []
            accounts_path = 'accounts'
            
            # First scan for files to move
            for folder in os.listdir(accounts_path):
                folder_path = os.path.join(accounts_path, folder)
                if os.path.isdir(folder_path):
                    for file in os.listdir(folder_path):
                        if file.startswith('generated_story') and file.endswith('.json'):
                            src_path = os.path.join(folder_path, file)
                            try:
                                with open(src_path, 'r', encoding='utf-8') as f:
                                    data = json.load(f)
                                    if 'story' in data:
                                        files_to_move.append({
                                            'src_path': src_path,
                                            'folder': folder,
                                            'file': file
                                        })
                            except Exception as e:
                                self.log_debug(f"Error processing {src_path}: {str(e)}")
            
            # Only create batch directory and move files if we have files to move
            moved_files = []
            batch_dir = None
            
            if files_to_move:
                os.makedirs('to_print', exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                batch_dir = os.path.join('to_print', f'batch_{timestamp}')
                os.makedirs(batch_dir, exist_ok=True)
                
                for file_info in files_to_move:
                    new_filename = f"{file_info['folder']}_{file_info['file']}"
                    dst_path = os.path.join(batch_dir, new_filename)
                    shutil.move(file_info['src_path'], dst_path)
                    moved_files.append(new_filename)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {
                'success': True,
                'batch_dir': batch_dir,
                'files': moved_files
            }
            self.wfile.write(json.dumps(response).encode())
        except Exception as e:
            self.log_debug(f"Error handling timer expiration: {str(e)}")
            self.send_error(500, str(e))

def start_file_watcher():
    accounts_path = 'accounts'
    event_handler = AccountsHandler()
    observer = Observer()
    observer.schedule(event_handler, accounts_path, recursive=True)
    observer.start()
    print(f"Started watching {accounts_path} for new JSON files...")
    return observer

def run_server():
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, CustomHandler)
    print('Server running on http://localhost:8000')
    httpd.serve_forever()

if __name__ == '__main__':
    observer = start_file_watcher()
    try:
        run_server()
    except KeyboardInterrupt:
        observer.stop()
        print("\nStopped watching for files.")
        observer.join()
        print("Server stopped.") 
