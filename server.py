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
            descriptions = data['descriptions']
            
            folder_path = os.path.join('accounts', folder)
            descriptions_file = os.path.join(folder_path, 'descriptions.json')
            
            try:
                # Save all descriptions to file
                with open(descriptions_file, 'w', encoding='utf-8') as f:
                    json.dump(descriptions, f, ensure_ascii=False, indent=2)
                
                # Create a summary file with all information
                summary_file = os.path.join(folder_path, 'summary.json')
                summary_data = {
                    'symbol': symbol,
                    'folder': folder,
                    'timestamp': datetime.now().isoformat(),
                    'total_images': len(descriptions),
                    'descriptions': descriptions
                }
                
                with open(summary_file, 'w', encoding='utf-8') as f:
                    json.dump(summary_data, f, ensure_ascii=False, indent=2)
                
                print(f"Sent all information for {symbol} ({folder}): {len(descriptions)} descriptions")
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = json.dumps({'success': True, 'message': f'Sent {len(descriptions)} descriptions'})
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