#!/usr/bin/env python3
import subprocess
import time
import sys
import os
import shutil
from pathlib import Path

def is_live_stream(url):
    try:
        # Check if the stream is currently live
        res = subprocess.run(["yt-dlp", "--print", "is_live", url], capture_output=True, text=True, timeout=30)
        output = res.stdout.strip().lower()
        return "true" in output
    except Exception as e:
        print(f"Error checking live status: {e}")
        return False

def smart_monitor(url, skip_upload=False):
    # Setup session dir to collect chunks
    session_id = str(int(time.time()))
    # Determine base directory
    script_dir = Path(__file__).resolve().parent
    base_dir = script_dir.parent
    staging_dir = base_dir / "staging"
    
    session_dir = staging_dir / f"session_{session_id}"
    session_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting Smart Monitor for {url}")
    print(f"Session Directory: {session_dir}")
    
    chunk_num = 1
    chunks = []
    
    while True:
        chunk_file = session_dir / f"chunk_{chunk_num:03d}.mp4"
        cmd = [
            "yt-dlp",
            "--wait-for-video", "60",
            "--extractor-args", "youtube:player_client=ios,android,web",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "-o", str(chunk_file),
            url
        ]
        
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Recording chunk {chunk_num:03d}...")
        subprocess.run(cmd)
        
        if chunk_file.exists() and chunk_file.stat().st_size > 0:
            chunks.append(chunk_file)
            chunk_num += 1
            
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] yt-dlp exited. Checking if stream is still live...")
        
        # Give YouTube a moment to update the stream status
        time.sleep(10) 
        
        if not is_live_stream(url):
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Stream is no longer live. Concluding broadcast.")
            break
        else:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Stream is still live! Network drop detected. Resuming capture...")
            
    if not chunks:
        print("No video chunks downloaded. Exiting.")
        shutil.rmtree(session_dir)
        return
        
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Broadcast concluded. Merging {len(chunks)} chunks...")
    concat_list = session_dir / "concat_list.txt"
    with open(concat_list, "w") as f:
        for c in chunks:
            f.write(f"file '{c.name}'\n")
            
    # Get metadata for the final filename
    meta_cmd = ["yt-dlp", "--print", "%(uploader)s_%(id)s", url]
    res = subprocess.run(meta_cmd, capture_output=True, text=True)
    prefix = res.stdout.strip() if res.returncode == 0 and res.stdout.strip() else f"unknown_{session_id}"
    
    # Clean the prefix to remove weird characters
    safe_prefix = "".join([c if c.isalnum() or c in ['_', '-'] else '_' for c in prefix])
    merged_file = staging_dir / f"ondemand_{safe_prefix}.mp4"
    
    if len(chunks) == 1:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Only 1 chunk recorded. Skipping FFmpeg merge to save disk space.")
        shutil.move(str(chunks[0]), str(merged_file))
    else:
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", "concat_list.txt",
            "-c", "copy",
            str(merged_file.resolve())
        ]
        
        try:
            subprocess.run(ffmpeg_cmd, check=True, cwd=str(session_dir), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"Merged successfully into {merged_file.name}")
        except subprocess.CalledProcessError as e:
            print(f"Error during FFmpeg merge: {e}")
            # If merge fails, just use the largest chunk so we don't lose data
            largest_chunk = max(chunks, key=lambda p: p.stat().st_size)
            shutil.move(str(largest_chunk), str(merged_file))
            print(f"Fallback: Moved largest chunk {largest_chunk.name} instead.")
    
    if not skip_upload:
        upload_script = script_dir / "upload_and_clean.sh"
        if upload_script.exists():
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Triggering post-processing AI Document Generation...")
            subprocess.run([str(upload_script), str(merged_file)])
        else:
            print("Upload script not found. Skipping post-processing.")
            
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Cleaning up session directory...")
    shutil.rmtree(session_dir)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: smart_monitor.py <url> [--skip-upload]")
        sys.exit(1)
        
    url = sys.argv[1]
    skip_upload = "--skip-upload" in sys.argv
    # Also support environment variable from telegram_listener
    if os.environ.get("SKIP_VIDEO_UPLOAD") == "1":
        skip_upload = True
        
    smart_monitor(url, skip_upload)
