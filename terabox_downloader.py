import os
import uuid
import json
import asyncio
import aiohttp
import logging
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

from config import BASE_DIR, DOWNLOAD_DIR, MAX_FILE_SIZE_BYTES

logger = logging.getLogger(__name__)

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
API_KEY_FILE = DATA_DIR / "terabox_api.json"

TERABOX_DOMAINS = [
    "terabox.com", "teraboxapp.com", "terabox.app", "1024tera.com",
    "4funbox.com", "4funbox.co", "mirrobox.com", "nephobox.com", 
    "freeterabox.com", "1024terabox.com", "terasharefile.com", 
    "teraboxshare.com", "momerybox.com", "terabox.fun", 
    "terafileshare.com", "teraboxlink.com", "terasharelink.com", 
    "dubox.com", "tibibox.com", "gibibox.com"
]

def get_terabox_api_key() -> str:
    if API_KEY_FILE.exists():
        try:
            with open(API_KEY_FILE, "r") as f:
                data = json.load(f)
                return data.get("api_key", "xapi_6508cf02b36060278ec89925ee153e6e")
        except Exception:
            pass
    return "xapi_6508cf02b36060278ec89925ee153e6e"

def set_terabox_api_key(api_key: str):
    with open(API_KEY_FILE, "w") as f:
        json.dump({"api_key": api_key}, f)

def is_terabox_url(url: str) -> bool:
    return any(domain in url.lower() for domain in TERABOX_DOMAINS)

async def extract_terabox_info(url: str) -> Tuple[bool, Dict[str, Any], Optional[str]]:
    api_key = get_terabox_api_key()
    api_url = "https://xapiverse.com/api/terabox"
    
    headers = {
        "Content-Type": "application/json",
        "xAPIverse-Key": api_key
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, headers=headers, json={"url": url}, timeout=25) as resp:
                if resp.status != 200:
                    return False, {}, f"API returned HTTP {resp.status}"
                
                data = await resp.json()
                
                if data.get("status") != "success":
                    return False, {}, f"API Error: {json.dumps(data)}"
                    
                files = data.get("list", [])
                if not files:
                    return False, {}, "No files found in this TeraBox link."
                    
                file_info = files[0]
                play_url = file_info.get("normal_dlink")
                
                if not play_url:
                    return False, {}, "No direct download link provided by the API."
                    
                title = file_info.get("name", "TeraBox_Video")
                thumb = file_info.get("thumbnail")
                
                duration_sec = None
                dur_str = file_info.get("duration", "")
                if dur_str and ":" in dur_str:
                    try:
                        parts = dur_str.split(":")
                        if len(parts) == 3:
                            duration_sec = int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
                        elif len(parts) == 2:
                            duration_sec = int(parts[0])*60 + int(parts[1])
                    except:
                        pass

                info = {
                    "id": uuid.uuid4().hex[:8],
                    "title": title,
                    "thumbnail": thumb,
                    "uploader": "xAPIverse",
                    "play_url": play_url,
                    "original_url": url,
                    "duration": duration_sec,
                    "formats": [],
                    "engine": "xapiverse",
                }
                return True, info, None
                
    except Exception as e:
        logger.exception("Error extracting Terabox info via xAPIverse")
        return False, {}, str(e)


async def _download_chunk(session, url, start, end, chunk_path):
    headers = {"Range": f"bytes={start}-{end}"}
    async with session.get(url, headers=headers) as resp:
        if resp.status not in (200, 206):
            raise Exception(f"Failed to fetch chunk. HTTP {resp.status}")
        with open(chunk_path, 'wb') as f:
            async for data in resp.content.iter_chunked(1024 * 1024):
                f.write(data)


async def download_terabox_media(url: str, quality: str = "720p", format_selector: str = None) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]], Optional[str]]:
    success, info, err = await extract_terabox_info(url)
    if not success:
        return False, None, None, err
        
    play_url = info["play_url"]
    file_id = info["id"]
    filename = info["title"]
    
    # Clean filename
    safe_title = "".join([c for c in filename if c.isalpha() or c.isdigit() or c in " ._-"]).rstrip()
    if not safe_title:
        safe_title = "terabox_video"
    if not safe_title.endswith(".mp4"):
        safe_title += ".mp4"
        
    file_path = os.path.join(DOWNLOAD_DIR, f"{file_id}_{safe_title}")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Get headers to check for multi-connection support
            async with session.head(play_url, allow_redirects=True) as resp:
                total_size = int(resp.headers.get("content-length", 0))
                accept_ranges = resp.headers.get("accept-ranges", "")
                
            if total_size > MAX_FILE_SIZE_BYTES:
                return False, None, None, f"File is too large ({total_size / (1024*1024):.1f} MB)."
                
            # If server supports ranges and file is > 5MB, use 8 concurrent connections!
            if total_size > 5 * 1024 * 1024 and accept_ranges == "bytes":
                num_connections = 8
                chunk_size = total_size // num_connections
                tasks = []
                chunk_files = []
                
                for i in range(num_connections):
                    start = i * chunk_size
                    end = start + chunk_size - 1 if i < num_connections - 1 else total_size - 1
                    chunk_path = f"{file_path}.part{i}"
                    chunk_files.append(chunk_path)
                    tasks.append(_download_chunk(session, play_url, start, end, chunk_path))
                
                # Download all chunks concurrently
                await asyncio.gather(*tasks)
                
                # Merge chunks
                with open(file_path, 'wb') as outfile:
                    for chunk_path in chunk_files:
                        with open(chunk_path, 'rb') as infile:
                            while True:
                                data = infile.read(1024 * 1024 * 5)
                                if not data:
                                    break
                                outfile.write(data)
                        os.remove(chunk_path) # Clean up partial
            else:
                # Single connection fallback
                async with session.get(play_url) as resp:
                    if resp.status != 200:
                        return False, None, None, f"Failed to download from CDN (HTTP {resp.status})"
                    with open(file_path, 'wb') as f:
                        async for chunk in resp.content.iter_chunked(1024 * 1024 * 2):
                            f.write(chunk)
                            
        return True, file_path, info, None
        
    except Exception as e:
        logger.exception("Failed to download Terabox media")
        # Cleanup
        if os.path.exists(file_path):
            os.remove(file_path)
        for i in range(16):
            if os.path.exists(f"{file_path}.part{i}"):
                os.remove(f"{file_path}.part{i}")
        return False, None, None, str(e)
