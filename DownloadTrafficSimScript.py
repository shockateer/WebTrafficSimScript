import requests
from bs4 import BeautifulSoup
import random
import time
import os
import sys
import shutil
import urllib3
from urllib.parse import urljoin, urlparse

# --- Configuration ---
TEST_DURATION_MINUTES = 5
LOOP_DELAY = 5

# Names of the input files (must be in same folder as script)
WEBSITE_LIST_FILE = "websites.txt"
FILE_LIST_FILE = "files.txt"

# --- SSL Warning Suppression ---
# Since we are ignoring SSL certificates, we suppress the warnings to keep the console clean.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_urls_from_file(filename):
    """Reads a text file and returns a list of non-empty URLs."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, filename)

    if not os.path.exists(file_path):
        print(f"WARNING: Could not find '{filename}' in {script_dir}")
        return []

    with open(file_path, 'r') as f:
        urls = [
            line.strip() for line in f 
            if line.strip() and not line.strip().startswith("#")
        ]
    return urls

# --- Function 1: Website Crawler ---
def test_website_traffic(url_list):
    if not url_list:
        return

    print("\n" + "="*80)
    print(f"STARTING WEBSITE CRAWL TEST (SSL Verify Disabled)")
    print("="*80)
    
    download_dir = "temp_web_cache"
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Bot/Testing'}

    print(f"{'Target Site':<30} | {'Size (MB)':<10} | {'Time (s)':<10} | {'Speed (Mbps)':<15}")
    print("-" * 75)

    for base_url in url_list:
        downloaded_files = []
        total_bytes = 0
        
        try:
            start_time = time.time()
            
            # 1. Download Base (verify=False ignores SSL errors)
            try:
                response = requests.get(base_url, headers=headers, timeout=10, verify=False)
                response.raise_for_status()
            except Exception as e:
                # Truncate error message if it's too long
                err_msg = str(e).split('\n')[0][:40]
                print(f"{base_url[:28]:<30} | Error: {err_msg}...")
                continue

            base_filename = os.path.join(download_dir, "base_page.html")
            with open(base_filename, 'wb') as f:
                f.write(response.content)
            downloaded_files.append(base_filename)
            total_bytes += len(response.content)

            # 2. Parse Links
            soup = BeautifulSoup(response.content, 'html.parser')
            all_links = [a.get('href') for a in soup.find_all('a', href=True)]
            
            valid_links = []
            for link in all_links:
                full_url = urljoin(base_url, link)
                parsed = urlparse(full_url)
                if parsed.scheme in ['http', 'https']:
                    valid_links.append(full_url)
            valid_links = list(set(valid_links))

            # 3. Random Sample
            num_to_choose = random.randint(2, 5)
            links_to_visit = random.sample(valid_links, min(len(valid_links), num_to_choose))

            # 4. Download Sub-links (verify=False)
            for i, link in enumerate(links_to_visit):
                try:
                    res = requests.get(link, headers=headers, timeout=10, verify=False)
                    if res.status_code == 200:
                        fname = os.path.join(download_dir, f"sub_page_{i}.html")
                        with open(fname, 'wb') as f:
                            f.write(res.content)
                        downloaded_files.append(fname)
                        total_bytes += len(res.content)
                except:
                    continue

            # 5. Stats
            duration = time.time() - start_time
            if duration == 0: duration = 0.001
            total_mb = total_bytes / (1024 * 1024)
            mbps = ((total_bytes * 8) / 1_000_000) / duration

            print(f"{base_url[:28]:<30} | {total_mb:<10.2f} | {duration:<10.2f} | {mbps:<15.2f}")

        finally:
            for f in downloaded_files:
                if os.path.exists(f):
                    os.remove(f)

    if os.path.exists(download_dir):
        try:
            shutil.rmtree(download_dir)
        except:
            pass

# --- Function 2: Large File Downloader ---
def format_size(size_in_bytes):
    if size_in_bytes >= 1024**3: return f"{size_in_bytes / (1024**3):.2f} GB"
    return f"{size_in_bytes / (1024**2):.2f} MB"

def test_large_file_traffic(url_list):
    if not url_list:
        return

    print("\n" + "="*80)
    print(f"STARTING LARGE FILE DOWNLOAD TEST (SSL Verify Disabled)")
    print("="*80)

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Bot/Testing'}
    print(f"{'File Name':<30} | {'Size':<10} | {'Time (s)':<10} | {'Avg Speed':<15}")
    print("-" * 75)

    for url in url_list:
        local_filename = url.split('/')[-1]
        if not local_filename: local_filename = "temp_large_file.dat"
        
        total_downloaded = 0
        start_time = time.time()
        
        try:
            # Added verify=False here
            with requests.get(url, headers=headers, stream=True, timeout=20, verify=False) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                
                with open(local_filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            total_downloaded += len(chunk)
                            
                            elapsed = time.time() - start_time
                            speed = (total_downloaded * 8) / (1_000_000 * elapsed) if elapsed > 0 else 0
                            
                            if total_size > 0:
                                percent = 100 * (total_downloaded / total_size)
                                bar_len = 20
                                filled = int(bar_len * total_downloaded // total_size)
                                bar = '█' * filled + '-' * (bar_len - filled)
                                sys.stdout.write(f"\rDownloading: |{bar}| {percent:5.1f}% @ {speed:5.2f} Mbps")
                            else:
                                sys.stdout.write(f"\rDownloading: {format_size(total_downloaded)} @ {speed:5.2f} Mbps")
                            sys.stdout.flush()

            duration = time.time() - start_time
            if duration == 0: duration = 0.001
            size_mb = total_downloaded / (1024 * 1024)
            avg_mbps = ((total_downloaded * 8) / 1_000_000) / duration

            sys.stdout.write("\r" + " " * 100 + "\r")
            print(f"{local_filename[:28]:<30} | {size_mb:<10.2f} | {duration:<10.2f} | {avg_mbps:<15.2f}")

        except Exception as e:
            sys.stdout.write("\r" + " " * 100 + "\r")
            err_msg = str(e).split('\n')[0][:40]
            print(f"Error downloading {local_filename}: {err_msg}...")
        finally:
            if os.path.exists(local_filename):
                os.remove(local_filename)

# --- Main Wrapper Loop ---
def main():
    print("Loading target lists...")
    websites = get_urls_from_file(WEBSITE_LIST_FILE)
    large_files = get_urls_from_file(FILE_LIST_FILE)

    print(f"Loaded {len(websites)} websites and {len(large_files)} large files.")

    if not websites and not large_files:
        print("Error: No URLs found in text files. Exiting.")
        return

    start_time = time.time()
    end_time = start_time + (TEST_DURATION_MINUTES * 60)
    iteration = 1
    
    print(f"Starting Bandwidth Stress Test for {TEST_DURATION_MINUTES} minutes.")
    print(f"Press Ctrl+C to stop manually.\n")

    try:
        while time.time() < end_time:
            current_time_str = time.strftime("%H:%M:%S", time.localtime())
            print(f"\n>>> ITERATION {iteration} STARTING AT {current_time_str} <<<")
            
            #test_website_traffic(websites)
            test_large_file_traffic(large_files)
            
            iteration += 1
            
            if time.time() < end_time:
                print(f"\nIteration complete. Cooling down for {LOOP_DELAY} seconds...")
                time.sleep(LOOP_DELAY)
            
    except KeyboardInterrupt:
        print("\n\nTest stopped by user.")
    
    print("\nTest Complete.")

if __name__ == "__main__":
    main()