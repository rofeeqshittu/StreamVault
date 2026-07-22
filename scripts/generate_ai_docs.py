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
        
        # In 2026, old models are locked for new users. 
        # We explicitly use gemini-flash-latest to let Google dynamically route 
        # to the newest active free-tier flash model (e.g. 3.5 or 3.6).
        target_model = 'gemini-flash-latest'
                
        print(f"Synthesizing Executive Brief via {target_model}...")
        response = client.models.generate_content(
            model=target_model,
            contents=[uploaded_file, prompt],
            config=types.GenerateContentConfig(temperature=0.2)
        )
        
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
    finally:
        print("Cleaning up Gemini File API resource...")
        client.files.delete(name=uploaded_file.name)
        # Clean up local mp3 if we extracted it
        if media_path.suffix == '.mp3':
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
