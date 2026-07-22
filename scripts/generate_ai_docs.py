#!/usr/bin/env python3
import os
import sys
import time
import subprocess
from pathlib import Path
from google import genai
from google.genai import types

def extract_audio(video_path: Path) -> Path:
    audio_path = video_path.with_suffix('.mp3')
    if audio_path.exists():
        return audio_path
    
    print(f"Extracting lightweight audio from {video_path.name}...")
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-acodec", "libmp3lame", "-b:a", "128k",
        str(audio_path)
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return audio_path
    except subprocess.CalledProcessError as e:
        print(f"Error extracting audio: {e}")
        sys.exit(1)

def generate_docs(media_path: Path):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set. Skipping AI generation.")
        sys.exit(0)

    client = genai.Client(api_key=api_key)
    
    print(f"Uploading {media_path.name} to Gemini...")
    uploaded_file = client.files.upload(file=str(media_path))
    
    print("Waiting for file processing to complete...")
    while True:
        file_info = client.files.get(name=uploaded_file.name)
        if file_info.state.name == "ACTIVE":
            break
        elif file_info.state.name == "FAILED":
            print("File processing failed.")
            sys.exit(1)
        time.sleep(5)

    prompt = """
    You are a Senior AI Systems Engineer specializing in automated media transcription and LLM document synthesis.
    Parse the provided stream recording and output a comprehensive, post-meeting executive document using this EXACT strict Markdown format:

    # 📌 StreamVault Executive Brief
    **Source Stream:** Extract from context
    **Date:** Extract from context

    ---

    ## 💡 Executive Summary
    [3-4 high-density paragraphs summarizing the core focus, context, and outcomes of the session]

    ---

    ## 🎯 Key Decisions & Action Items
    - [ ] **Action Item:** Description, owner, or context mentioned
    - [ ] **Core Decision:** Key choices or resolutions finalized during the stream

    ---

    ## ⏱️ Timestamped Agenda & Discussion Breakdown
    - **[00:00 - 15:30] Introduction & Setup:** Detailed key points...
    - **[15:31 - 45:00] Deep Dive / Live Demonstration:** Tools mentioned, code walkthroughs, concepts...
    - **[45:01 - End] Q&A & Wrap-Up:** Audience questions and direct responses given...

    ---

    ## 🛠️ Tools, 3rd Party Software & Insights Mentioned
    * List all software, frameworks, APIs, external services, or strategic insights highlighted in the stream.

    ---

    ## 🧠 Strategic Frameworks & Key Takeaways
    * Core concepts and takeaways formulated during the broadcast.
    """

    print("Synthesizing Executive Brief via Gemini 1.5 Pro...")
    try:
        response = client.models.generate_content(
            model='gemini-1.5-pro',
            contents=[uploaded_file, prompt],
            config=types.GenerateContentConfig(temperature=0.2)
        )
        
        md_path = media_path.with_suffix('.md')
        with open(md_path, "w") as f:
            f.write(response.text)
        print(f"Successfully generated: {md_path.name}")
        
    except Exception as e:
        print(f"Error during generation: {e}")
    finally:
        print("Cleaning up Gemini File API resource...")
        client.files.delete(name=uploaded_file.name)
        # Clean up local mp3 if we extracted it
        if media_path.suffix == '.mp3':
            os.remove(media_path)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: generate_ai_docs.py <video_file>")
        sys.exit(1)
        
    video_path = Path(sys.argv[1])
    if not video_path.exists():
        print(f"File not found: {video_path}")
        sys.exit(1)
        
    # Check if a VTT transcript exists
    vtt_path = video_path.with_suffix('.en.vtt')
    if not vtt_path.exists():
        vtt_path = video_path.with_suffix('.vtt')
        
    if vtt_path.exists():
        print(f"Found transcript: {vtt_path.name}")
        generate_docs(vtt_path)
    else:
        audio_path = extract_audio(video_path)
        generate_docs(audio_path)
