from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os
import base64
from datetime import datetime
from urllib.parse import parse_qs
import threading
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import shutil

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
                    with open(json_file, 'r') as f:
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
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            # Check if the file has already been printed
            if data.get('printed', False):
                print(f"File {file_path} has already been processed")
                return
                
            # Check for content section
            if 'content' in data:
                print(f"New story detected: {file_path}")
                
                # Update the file to mark it as printed
                data['printed'] = True
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2)
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
                            with open(json_file, 'r') as f:
                                data = json.load(f)
                                emoji_map[folder] = data.get('emoji', '📚')
                
                # Find all story JSON files
                for folder in os.listdir(accounts_path):
                    folder_path = os.path.join(accounts_path, folder)
                    if os.path.isdir(folder_path):
                        for file in os.listdir(folder_path):
                            if file.endswith('.json') and file != f'{folder}.json':
                                file_path = os.path.join(folder_path, file)
                                with open(file_path, 'r') as f:
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
        
        # Handle /timer-expired endpoint
        elif self.path.rstrip('/') == '/timer-expired':
            try:
                # Create to_print directory if it doesn't exist
                os.makedirs('to_print', exist_ok=True)
                
                # Get current timestamp for the batch
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                
                # Create a new directory for this batch
                batch_dir = os.path.join('to_print', f'batch_{timestamp}')
                os.makedirs(batch_dir, exist_ok=True)
                
                # Track all files we're going to move
                moved_files = []
                
                # Go through all account folders
                accounts_path = 'accounts'
                for folder in os.listdir(accounts_path):
                    folder_path = os.path.join(accounts_path, folder)
                    if os.path.isdir(folder_path):
                        # Skip the folder definition file
                        for file in os.listdir(folder_path):
                            if file.endswith('.json') and file != f'{folder}.json':
                                src_path = os.path.join(folder_path, file)
                                # Create a new filename that includes the folder name
                                new_filename = f"{folder}_{file}"
                                dst_path = os.path.join(batch_dir, new_filename)
                                
                                try:
                                    # Copy the file instead of moving it
                                    shutil.copy2(src_path, dst_path)
                                    moved_files.append(new_filename)
                                except Exception as e:
                                    print(f"Error copying {src_path}: {str(e)}")
                
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