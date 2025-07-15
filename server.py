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

# Configure Gemini API
def configure_gemini():
    """Configure the Gemini API with your API key"""
    # You'll need to set your API key as an environment variable
    # export GOOGLE_API_KEY="your-api-key-here"
    api_key = "AIzaSyDF65s7VX0L_6pmRWmzQtSYV3D5Wn0AJjE"
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
        
        # Skip folder definition files
        if file_name == f'{folder_name}.json':
            return
            
        try:
            # Wait a brief moment to ensure file is fully written
            time.sleep(0.1)
            
            # Read and process the JSON file
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Check for content section
            if 'content' in data:
                print(f"New story detected: {file_path}")
            else:
                print(f"No content section found in {file_path}")
                
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")

class CustomHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        # Handle /get-stories endpoint first
        if self.path.rstrip('/') == '/get-stories':
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
                            if file.endswith('.json') and file != f'{folder}.json':
                                file_path = os.path.join(folder_path, file)
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    data = json.load(f)
                                    if 'content' in data:
                                        story = {
                                            'id': os.path.splitext(file)[0],
                                            'emoji': emoji_map.get(folder, '📚'),
                                            'title': data.get('title', 'Neue Geschichte'),
                                            'content': data['content']
                                        }
                                        stories.append(story)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(stories).encode())
                return
            except Exception as e:
                print(f"Error getting stories: {str(e)}")
                self.send_error(500, str(e))
                return
        
        # Handle image listing endpoint (from station_2)
        elif self.path.startswith('/list-images/'):
            folder_name = self.path.split('/list-images/')[1]
            folder_path = os.path.join('accounts', folder_name)
            print(f"Listing images for folder: {folder_path}")

            try:
                image_files = []
                if os.path.exists(folder_path):
                    for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif']:
                        pattern = os.path.join(folder_path, ext)
                        files = glob.glob(pattern)
                        for file in files:
                            image_files.append(os.path.basename(file))
                
                print(f"Found {len(image_files)} images")
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = json.dumps({'images': image_files})
                self.wfile.write(response.encode())
                return
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = json.dumps({'error': str(e)})
                self.wfile.write(response.encode())
                return
        
        # Handle loading descriptions endpoint (from station_2)
        elif self.path.startswith('/load-descriptions/'):
            folder_name = self.path.split('/load-descriptions/')[1]
            descriptions_file = os.path.join('accounts', folder_name, 'descriptions.json')
            print(f"Loading descriptions for {folder_name}, file: {descriptions_file}")
            print(f"File exists: {os.path.exists(descriptions_file)}")
            
            try:
                descriptions = {}
                if os.path.exists(descriptions_file):
                    with open(descriptions_file, 'r', encoding='utf-8') as f:
                        descriptions = json.load(f)
                    
                    # Handle backward compatibility - convert old format to new format
                    for image_name, description_data in descriptions.items():
                        if isinstance(description_data, str):
                            # Old format - convert to new format
                            descriptions[image_name] = {
                                'description': description_data,
                                'useImage': False
                            }
                        elif isinstance(description_data, dict) and 'useImage' in description_data:
                            # Convert string useImage values to boolean
                            if isinstance(description_data['useImage'], str):
                                descriptions[image_name]['useImage'] = description_data['useImage'].lower() in ['true', 'yes', '1']
                    
                    print(f"Loaded descriptions: {descriptions}")
                else:
                    print(f"Descriptions file not found: {descriptions_file}")
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = json.dumps({'descriptions': descriptions})
                self.wfile.write(response.encode())
                return
            except Exception as e:
                print(f"Error loading descriptions: {e}")
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = json.dumps({'error': str(e)})
                self.wfile.write(response.encode())
                return
        
        # Handle requests for images in accounts folder (from station_2)
        elif self.path.startswith('/accounts/'):
            # Remove /accounts/ prefix and decode URL
            print(f"Original path: {self.path}")
            file_path = unquote(self.path)
            file_path = '.' + file_path
            print(f"Requesting account file: {file_path}")
            
            print(f"File exists: {os.path.exists(file_path)}")
            print(f"Is file: {os.path.isfile(file_path)}")
            
            if os.path.exists(file_path) and os.path.isfile(file_path):
                self.send_response(200)
                # Set appropriate content type based on file extension
                if file_path.endswith('.jpg') or file_path.endswith('.jpeg'):
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
                print("File sent successfully")
                return
            else:
                self.send_response(404)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'File not found')
                return
        
        # Handle /timer-expired endpoint
        elif self.path.rstrip('/') == '/timer-expired':
            try:
                print("Timer expired endpoint called")
                # Create to_print directory if it doesn't exist
                os.makedirs('to_print', exist_ok=True)
                print("Created to_print directory")
                
                # Get current timestamp for the batch
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                
                # Create a new directory for this batch
                batch_dir = os.path.join('to_print', f'batch_{timestamp}')
                os.makedirs(batch_dir, exist_ok=True)
                print(f"Created batch directory: {batch_dir}")
                
                # Track all files we're going to move
                moved_files = []
                
                # Go through all account folders
                accounts_path = 'accounts'
                print(f"Scanning accounts directory: {accounts_path}")
                
                for folder in os.listdir(accounts_path):
                    folder_path = os.path.join(accounts_path, folder)
                    print(f"Checking folder: {folder_path}")
                    if os.path.isdir(folder_path):
                        # Skip the folder definition file
                        for file in os.listdir(folder_path):
                            if file.endswith('.json') and file != f'{folder}.json':
                                src_path = os.path.join(folder_path, file)
                                print(f"Found JSON file: {src_path}")
                                
                                # Read the file to check if it has content
                                try:
                                    with open(src_path, 'r', encoding='utf-8') as f:
                                        data = json.load(f)
                                        if 'content' in data:
                                            # Create a new filename that includes the folder name
                                            new_filename = f"{folder}_{file}"
                                            dst_path = os.path.join(batch_dir, new_filename)
                                            print(f"Moving {src_path} to {dst_path}")
                                            
                                            # Move the file instead of copying
                                            shutil.move(src_path, dst_path)
                                            moved_files.append(new_filename)
                                            print(f"Successfully moved {new_filename}")
                                except Exception as e:
                                    print(f"Error processing {src_path}: {str(e)}")
                
                print(f"Total files copied: {len(moved_files)}")
                print(f"Files: {moved_files}")
                
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
                return
            except Exception as e:
                print(f"Error handling timer expiration: {str(e)}")
                self.send_error(500, str(e))
                return
        
        # If not a special endpoint, serve files from the current directory
        try:
            # Remove leading slash and normalize path
            path = self.path.lstrip('/')
            if not path or path.endswith('/'):
                path = path + 'index.html'
                
            # Check if file exists in station_3 directory
            if os.path.exists(os.path.join('station_3', path)):
                self.path = '/station_3/' + path
            elif os.path.exists(os.path.join('station_2', path)):
                self.path = '/station_2/' + path
            elif os.path.exists(os.path.join('station_1', path)):
                self.path = '/station_1/' + path
                
            return SimpleHTTPRequestHandler.do_GET(self)
        except Exception as e:
            print(f"Error serving file: {str(e)}")
            self.send_error(500, str(e))

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