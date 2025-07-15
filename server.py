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

class AccountsHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        
        # Check if it's a JSON file
        if not event.src_path.endswith('.json'):
            return
            
        # Get the file path
        file_path = event.src_path
        
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
                print(f"New file detected: {file_path}")
                print(f"Content found: {data['content']}")
                # Here you can add your processing logic for the content
                
                # Update the file to mark it as printed
                data['printed'] = True
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2)
            else:
                print(f"No content section found in {file_path}")
                
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")

class CustomHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/save-image':
            # Read the content length
            content_length = int(self.headers['Content-Length'])
            # Read the POST data
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Get image data and folder
            image_data = data['imageData']
            folder = data['folder']
            
            # Remove the data URL prefix
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            
            # Create timestamp for filename
            timestamp = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
            filename = f'photo_{timestamp}.jpg'
            
            # Ensure the accounts folder exists
            folder_path = os.path.join('station_1', 'accounts', folder)
            os.makedirs(folder_path, exist_ok=True)
            
            # Save the image
            file_path = os.path.join(folder_path, filename)
            with open(file_path, 'wb') as f:
                f.write(base64.b64decode(image_data))
            
            # Create JSON file with the same name
            json_data = {
                'image_file': filename,
                'timestamp': timestamp,
                'printed': False,
                'content': f'New image captured for {folder}'
            }
            json_path = os.path.join(folder_path, f'{os.path.splitext(filename)[0]}.json')
            with open(json_path, 'w') as f:
                json.dump(json_data, f, indent=2)
            
            # Send response
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
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def end_headers(self):
        # Enable CORS
        self.send_header('Access-Control-Allow-Origin', '*')
        SimpleHTTPRequestHandler.end_headers(self)

def start_file_watcher():
    # Path to the accounts directory
    accounts_path = os.path.join('station_1', 'accounts')
    
    # Create an observer and handler
    event_handler = AccountsHandler()
    observer = Observer()
    
    # Schedule watching of all subdirectories
    observer.schedule(event_handler, accounts_path, recursive=True)
    
    # Start the observer
    observer.start()
    print(f"Started watching {accounts_path} for new JSON files...")
    
    return observer

def run_server():
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, CustomHandler)
    print('Server running on port 8000...')
    httpd.serve_forever()

if __name__ == '__main__':
    # Start the file watcher in a separate thread
    observer = start_file_watcher()
    
    try:
        # Start the HTTP server in the main thread
        run_server()
    except KeyboardInterrupt:
        observer.stop()
        print("\nStopped watching for files.")
        observer.join()
        print("Server stopped.") 