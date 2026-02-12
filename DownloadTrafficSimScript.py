import requests
from bs4 import BeautifulSoup
import random
import time
import os
import sys
import shutil
import urllib3
import warnings
import argparse
import datetime
import socket
from urllib.parse import urljoin, urlparse

# --- Configuration ---
TEST_DURATION_MINUTES = 5
LOOP_DELAY = 5
LOG_FOLDER_NAME = "OUTPUT_LOGS"

# --- SSL & Warning Suppression ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=UserWarning, module='bs4')

# --- Global Logger Setup ---
CURRENT_LOG_FILE = None
# Cache for DNS and GeoIP to avoid rate limiting and speed up loops
# Format: { 'hostname': {'ip': '1.2.3.4', 'cc': 'US'} }
HOST_CACHE = {}

def setup_logging():
    """Creates the log directory and generates the log filename for this run."""
    global CURRENT_LOG_FILE
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(script_dir, LOG_FOLDER_NAME)
    
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
        except OSError as e:
            print(f"Error creating log directory: {e}")
            return

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"bandwidth_test_{timestamp}.log"
    CURRENT_LOG_FILE = os.path.join(log_dir, filename)
    
    with open(CURRENT_LOG_FILE, 'w', encoding='utf-8') as f:
        f.write(f"--- Bandwidth Test Log: {timestamp} ---\n")
    
    print(f"Logging output to: {CURRENT_LOG_FILE}")

def log(message, end="\n"):
    """Prints to console AND appends to the log file with a timestamp."""
    print(message, end=end)
    
    if CURRENT_LOG_FILE:
        try:
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(CURRENT_LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(f"[{ts}] {message}\n")
        except Exception:
            pass

def get_system_public_ip():
    """Fetches the external public IP address of this system."""
    try:
        # api.ipify.org is a simple service that returns just the IP as text
        response = requests.get('https://api.ipify.org', timeout=5)
        if response.status_code == 200:
            return response.text.strip()
    except Exception:
        return "Unavailable"
    return "Unavailable"

def get_ip_info(url):
    """
    Resolves DNS and performs a simplified GeoIP lookup.
    Returns a dict with 'ip' and 'cc' (Country Code).
    """
    try:
        parsed = urlparse(url)
        hostname = parsed.netloc
        
        # Return cached result if we already looked this up
        if hostname in HOST_CACHE:
            return HOST_CACHE[hostname]

        # 1. Resolve IP
        ip = socket.gethostbyname(hostname)

        # 2. Lookup Country (Using ip-api.com free API)
        country_code = "??"
        try:
            # Short timeout to prevent hanging the script on geo lookup
            geo_resp = requests.get(f"http://ip-api.com/json/{ip}", timeout=2)
            if geo_resp.status_code == 200:
                data = geo_resp.json()
                country_code = data.get('countryCode', '??')
        except:
            country_code = "Err"

        result = {'ip': ip, 'cc': country_code}
        HOST_CACHE[hostname] = result
        return result

    except Exception:
        return {'ip': 'N/A', 'cc': 'N/A'}

def get_urls_from_file(filename):
    """Reads a text file and returns a list of non-empty URLs."""
    if os.path.exists(filename):
        file_path = filename
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, filename)

    if not os.path.exists(file_path):
        log(f"WARNING: Could not find '{filename}'")
        return []

    log(f"Reading targets from: {file_path}")
    with open(file_path, 'r') as f:
        urls = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
    return urls

# --- Function 1: Website Crawler ---
def test_website_traffic(url_list):
    if not url_list:
        return

    log("\n" + "="*130)
    log(f"STARTING WEBSITE CRAWL TEST (SSL Verify Disabled)")
    log("="*130)
    
    download_dir = "temp_web_cache"
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Bot/Testing'}

    # Updated Table Header
    log(f"{'Target Site':<60} | {'IP Address':<15} | {'CC':<4} | {'Size (MB)':<10} | {'Time (s)':<10} | {'Speed (Mbps)':<15}")
    log("-" * 130)

    for base_url in url_list:
        downloaded_files = []
        total_bytes = 0
        
        # Resolve IP/Country before starting download
        info = get_ip_info(base_url)
        ip_display = info['ip']
        cc_display = info['cc']
        
        try:
            start_time = time.time()
            
            # 1. Download Base
            try:
                response = requests.get(base_url, headers=headers, timeout=10, verify=False)
                response.raise_for_status()
            except Exception as e:
                # Truncate base_url to 58 chars to fit in 60 column
                log(f"{base_url[:58]:<60} | {ip_display:<15} | {cc_display:<4} | FAILED")
                log(f"    >>> ERROR: {e}")
                continue

            base_filename = os.path.join(download_dir, "base_page.html")
            with open(base_filename, 'wb') as f:
                f.write(response.content)
            downloaded_files.append(base_filename)
            total_bytes += len(response.content)

            # 2. Parse Links
            try:
                soup = BeautifulSoup(response.content, 'lxml')
            except:
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

            # 4. Download Sub-links
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

            # Truncate base_url to 58 chars to fit in 60 column
            log(f"{base_url[:58]:<60} | {ip_display:<15} | {cc_display:<4} | {total_mb:<10.2f} | {duration:<10.2f} | {mbps:<15.2f}")

        except Exception as e:
            log(f"{base_url[:58]:<60} | {ip_display:<15} | {cc_display:<4} | FAILED (General)")
            log(f"    >>> ERROR: {e}")

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

    log("\n" + "="*130)
    log(f"STARTING LARGE FILE DOWNLOAD TEST (SSL Verify Disabled)")
    log("="*130)

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Bot/Testing'}
    
    # Updated Table Header (60 chars for File URL)
    log(f"{'File URL':<60} | {'IP Address':<15} | {'CC':<4} | {'Size':<10} | {'Time (s)':<10} | {'Avg Speed':<15}")
    log("-" * 130)

    for url in url_list:
        local_filename = url.split('/')[-1]
        if not local_filename: local_filename = "temp_large_file.dat"
        
        # Resolve IP/Country
        info = get_ip_info(url)
        ip_display = info['ip']
        cc_display = info['cc']

        total_downloaded = 0
        start_time = time.time()
        
        try:
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
                            
                            # Progress Bar (Console Only)
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
            
            # Log Result with IP and CC, truncated URL to 58 chars
            log(f"{url[:58]:<60} | {ip_display:<15} | {cc_display:<4} | {size_mb:<10.2f} | {duration:<10.2f} | {avg_mbps:<15.2f}")

        except Exception as e:
            sys.stdout.write("\r" + " " * 100 + "\r")
            log(f"{url[:58]:<60} | {ip_display:<15} | {cc_display:<4} | FAILED")
            log(f"    >>> ERROR: {e}")
            
        finally:
            if os.path.exists(local_filename):
                os.remove(local_filename)

# --- Main Wrapper Loop ---
def main():
    setup_logging()

    # --- Display System Public IP ---
    log("Checking System Public IP Address...")
    public_ip = get_system_public_ip()
    log(f"System Public IP: {public_ip}")
    log("-" * 30)

    parser = argparse.ArgumentParser(description="Bandwidth Stress Tester")
    parser.add_argument("-w", "--websites", type=str, default="websites.txt", help="Path to websites file")
    parser.add_argument("-f", "--files", type=str, default="files.txt", help="Path to large files file")
    
    args = parser.parse_args()

    log("Loading target lists...")
    websites = get_urls_from_file(args.websites)
    large_files = get_urls_from_file(args.files)

    log(f"Loaded {len(websites)} websites and {len(large_files)} large files.")

    if not websites and not large_files:
        log("Error: No URLs found in text files. Exiting.")
        return

    start_time = time.time()
    end_time = start_time + (TEST_DURATION_MINUTES * 60)
    iteration = 1
    
    log(f"Starting Bandwidth Stress Test for {TEST_DURATION_MINUTES} minutes.")
    log(f"Press Ctrl+C to stop manually.\n")

    try:
        while time.time() < end_time:
            current_time_str = time.strftime("%H:%M:%S", time.localtime())
            log(f"\n>>> ITERATION {iteration} STARTING AT {current_time_str} <<<")
            
            #test_website_traffic(websites)
            test_large_file_traffic(large_files)
            
            iteration += 1
            
            if time.time() < end_time:
                log(f"\nIteration complete. Cooling down for {LOOP_DELAY} seconds...")
                time.sleep(LOOP_DELAY)
            
    except KeyboardInterrupt:
        log("\n\nTest stopped by user.")
    
    log("\nTest Complete.")

if __name__ == "__main__":
    main()