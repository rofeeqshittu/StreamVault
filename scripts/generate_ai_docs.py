#!/usr/bin/env python3
import os
import sys
import time
import subprocess
from pathlib import Path
from google import genai
from google.genai import types

def extract_audio(video_path: Path) -> Path:
    # First check if audio already extracted
    for ext in ('.m4a', '.mp3'):
        candidate = video_path.with_suffix(ext)
        if candidate.exists() and candidate.stat().st_size > 0:
            return candidate

    print(f"Extracting lightweight audio from {video_path.name}...")
    # Fast stream-copy first (instantaneous, 0 CPU re-encoding overhead)
    m4a_path = video_path.with_suffix('.m4a')
    copy_cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-c:a", "copy",
        str(m4a_path)
    ]
    try:
        subprocess.run(copy_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if m4a_path.exists() and m4a_path.stat().st_size > 0:
            print("Extracted audio via stream-copy in seconds.")
            return m4a_path
    except subprocess.CalledProcessError:
        pass

    # Fallback to fast mono mp3 transcode if stream-copy is incompatible
    mp3_path = video_path.with_suffix('.mp3')
    fallback_cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-acodec", "libmp3lame", "-b:a", "64k", "-ac", "1",
        str(mp3_path)
    ]
    try:
        subprocess.run(fallback_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return mp3_path
    except subprocess.CalledProcessError as e:
        print(f"Error extracting audio: {e}")
        sys.exit(1)

def generate_docs(media_path: Path):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set. Skipping AI generation.")
        sys.exit(0)

    # Configure a 10-minute timeout (600,000 ms) for generation
    client = genai.Client(api_key=api_key, http_options={'timeout': 600000})
    # Configure a 60-minute timeout (3,600,000 ms) for uploading large audio files
    upload_client = genai.Client(api_key=api_key, http_options={'timeout': 3600000})
    
    import shutil
    import time
    
    # Strip non-ASCII characters to keep the original name safe for HTTP upload
    safe_name_str = media_path.name.encode('ascii', 'ignore').decode('ascii')
    # If the name was entirely non-ASCII (e.g., full Arabic/Chinese title), fallback to timestamp
    if len(safe_name_str) <= 4:
        safe_name_str = f"upload_{int(time.time())}{media_path.suffix}"
    else:
        safe_name_str = f"gemini_{safe_name_str}"
        
    safe_path = media_path.with_name(safe_name_str)
    os.rename(media_path, safe_path)
    
    print(f"Uploading {media_path.name} to Gemini...")
    uploaded_file = None
    try:
        uploaded_file = upload_client.files.upload(file=str(safe_path))
    finally:
        if safe_path.exists():
            os.remove(safe_path)
    
    print("Waiting for file processing to complete...")
    while True:
        file_info = upload_client.files.get(name=uploaded_file.name)
        if file_info.state.name == "ACTIVE":
            break
        elif file_info.state.name == "FAILED":
            print("File processing failed.")
            sys.exit(1)
        time.sleep(5)

    prompt = """
    You are a Principal AI Systems Engineer and Expert Technical Analyst.
    Your objective is to parse the provided 6-hour stream recording/transcript and output a hyper-detailed, comprehensive executive document.
    
    CRITICAL INSTRUCTION: You are processing a long-context file. DO NOT summarize or skip over technical details. You must be exhaustive. If a tool, framework, specific strategy, or action item is mentioned at ANY point in the stream, it MUST be extracted and documented. Expand on points deeply rather than glossing over them. Use maximum analytical depth.

    Output using clean, highly readable PLAIN TEXT format. DO NOT use markdown symbols like asterisks or hashes. Use simple spacing and all-caps headings so it looks beautiful in any standard text reader (like Notepad or a mobile phone viewer).

    Format the document with these clear sections:
    
    STREAMVAULT EXECUTIVE BRIEF
    Source Stream: [Extract from context]
    Date: [Extract from context]
    
    EXECUTIVE SUMMARY
    [3-5 high-density paragraphs summarizing the core focus, context, and all major outcomes of the session. Be specific.]
    
    KEY DECISIONS & ACTION ITEMS
    [Action Item]: [Specific task], [Owner if mentioned], [Context]
    [Core Decision]: [Key choices or resolutions finalized during the stream]
    
    TIMESTAMPED AGENDA & DISCUSSION BREAKDOWN
    [00:00 - 15:30] Phase 1: [Topic]
      - Detail 1...
      - Detail 2...
      
    TOOLS, 3RD PARTY SOFTWARE & TECHNICAL INSIGHTS
    List EVERY piece of software, framework, API, external service, or strategic insight highlighted in the stream. Explain HOW it was used.
    
    STRATEGIC FRAMEWORKS & KEY TAKEAWAYS
    Deep-dive bullet points covering foundational concepts, workflows, and takeaways formulated during the broadcast.
    """

    print("Querying available Gemini models...")
    try:
        available_models = [m.name.replace('models/', '') for m in client.models.list()]
        print(f"Found models: {available_models}")
        
        target_model = None
        for preferred in [
            'gemini-3.8-flash',
            'gemini-3.7-flash',
            'gemini-3.6-flash',
            'gemini-3.5-flash',
            'gemini-flash-latest'
        ]:
            if preferred in available_models:
                target_model = preferred
                break
        if not target_model:
            flash_models = [m for m in available_models if 'flash' in m and 'preview' not in m and 'tts' not in m and 'image' not in m]
            target_model = flash_models[0] if flash_models else 'gemini-3.8-flash'
                
        print(f"Synthesizing Executive Brief via {target_model}...")
        
        # Robust retry loop for transient network/API drops during long generations
        max_retries = 3
        response = None
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=target_model,
                    contents=[uploaded_file, prompt],
                    config=types.GenerateContentConfig(temperature=0.2)
                )
                break
            except Exception as e:
                print(f"Generation attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise e
                time.sleep(15 * (attempt + 1))
        
        import docx
        
        docx_path = media_path.with_suffix('.docx')
        doc = docx.Document()
        
        # Split text by newline and add as paragraphs to keep it clean
        for line in response.text.split('\n'):
            doc.add_paragraph(line)
            
        doc.save(docx_path)
        print(f"Successfully generated: {docx_path.name}")
        
    except Exception as e:
        print(f"Error during generation: {e}")
        # Create an error DOCX so the user knows exactly why it failed (e.g. Safety Filters)
        import docx
        docx_path = media_path.with_suffix('.docx')
        doc = docx.Document()
        doc.add_heading("AI Generation Failed", level=1)
        doc.add_paragraph(f"The AI was unable to generate the brief. This usually happens if the content triggers Google's safety filters (e.g. profanity, dangerous content) or if the audio was too large.")
        doc.add_paragraph(f"Error Details: {str(e)}")
        doc.save(docx_path)
    finally:
        if uploaded_file is not None:
            print("Cleaning up Gemini File API resource...")
            try:
                upload_client.files.delete(name=uploaded_file.name)
            except Exception:
                pass
        # Clean up local audio if we extracted it
        if media_path.suffix in ('.mp3', '.m4a') and media_path.exists():
            try:
                os.remove(media_path)
            except OSError:
                pass

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: generate_ai_docs.py <video_file>")
        sys.exit(1)
        
    video_path = Path(sys.argv[1])
    if not video_path.exists():
        print(f"File not found: {video_path}")
        sys.exit(1)
        
    # We explicitly extract MP3 audio and feed it directly to Gemini.
    # Gemini's native audio engine is vastly superior to YouTube's auto-captions
    # for picking up technical jargon, speaker changes, and nuances.
    audio_path = extract_audio(video_path)
    generate_docs(audio_path)
