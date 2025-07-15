import time
import json
import os
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

def start_watching():
    # Path to the accounts directory
    accounts_path = os.path.join(os.path.dirname(__file__), 'accounts')
    
    # Create an observer and handler
    event_handler = AccountsHandler()
    observer = Observer()
    
    # Schedule watching of all subdirectories
    observer.schedule(event_handler, accounts_path, recursive=True)
    
    # Start the observer
    observer.start()
    print(f"Started watching {accounts_path} for new JSON files...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nStopped watching for files.")
    
    observer.join()

if __name__ == "__main__":
    start_watching() 