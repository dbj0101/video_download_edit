import subprocess
import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv
from moviepy import VideoFileClip, concatenate_videoclips

# 1. Load the .env file
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
env_prompt = os.getenv("GEMINI_PROMPT")

if api_key:
    genai.configure(api_key=api_key)

def countdown_sleep(seconds, message):
    """Writes a countdown on one line that gets replaced."""
    for i in range(seconds, 0, -1):
        # \r moves the cursor back to the start; end="" prevents a new line
        print(f"\r{message} in {i}s...   ", end="", flush=True)
        time.sleep(1)
    # Clear the line or move to next after finishing
    print(f"\r{message}... COMPLETE!          ")

def process_with_gemini(video_path):
    default_prompt = (
        "Identify every segment where Laura is speaking and where Aaron is speaking. "
        "Return a valid JSON list of lists: [[start, end, label]]. "
        "Include all of Laura; only 1 second of Aaron."
    )
    prompt = env_prompt if env_prompt else default_prompt

    segments_filename = f"{video_path.stem}_keep_segments.json"
    segments_path = video_path.parent / segments_filename
    
    if segments_path.exists():
        print(f"📄 JSON segments already exist: {segments_path.name}. Skipping Gemini upload.")
        return segments_path

    print(f"🧠 Uploading for speaker analysis: {video_path.name}...")
    video_file = genai.upload_file(path=video_path)
    
    while video_file.state.name == "PROCESSING":
        # Using the new countdown method here
        countdown_sleep(20, "⏳ Gemini is indexing video frames")
        video_file = genai.get_file(video_file.name)

    if video_file.state.name == "FAILED":
        print("❌ Video processing failed.")
        return None

    print("✅ Video ready. Generating speaker-specific segments...")
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    model = genai.GenerativeModel(model_name=model_name)
    response = model.generate_content([video_file, prompt])
    
    clean_json = response.text.replace("```json", "").replace("```", "").strip()
    
    with open(segments_path, "w") as f:
        f.write(clean_json)
    
    print(f"📄 Segments file generated: {segments_path.name}")
    return segments_path

def apply_moviepy_cuts(video_path, keep_segments_path):
    # Requirement 1: Changed suffix to Segments_Cut.mp4
    output_file = video_path.parent / f"{video_path.stem}_Segments_Cut.mp4"
    
    print(f"🎬 Performing surgical cuts on {video_path.name}...")
    
    try:
        with open(keep_segments_path, "r") as f:
            keep_segments = json.load(f)
        
        video = VideoFileClip(str(video_path))
        clips = []

        for segment in keep_segments:
            start, end, label = segment
            end_time = min(end, video.duration)
            clips.append(video.subclipped(start, end_time))

        final_video = concatenate_videoclips(clips)
        final_video.write_videofile(str(output_file), codec="libx264", audio_codec="aac")
        
        video.close()
        print(f"✨ Success! Saved to {output_file.name}")
        return output_file

    except Exception as e:
        print(f"❌ MoviePy Error: {e}")
        return None

def download_and_open():
    # Requirement 3 & 4: Added --skipEditMovie and --skipAPI arguments
    if len(sys.argv) < 2:
        print("❌ Usage: python3 import_video.py <URL> [--skipEditMovie] [--skipAPI]")
        return

    video_url = sys.argv[1]
    skip_edit = "--skipEditMovie" in sys.argv
    skip_api = "--skipAPI" in sys.argv
    
    # Requirement 2: Changed prefix from GA_ to VF_
    today_str = datetime.now().strftime("%Y%m%d")
    filename = f"VF_{today_str}.mp4" 

    current_dir = Path(__file__).parent
    import_folder = current_dir / "imported"
    import_folder.mkdir(exist_ok=True)
    download_path = import_folder / filename

    if download_path.exists():
        print(f"📂 Video already exists: {download_path.name}. Skipping download.")
    else:
        print(f"🌐 Downloading: {video_url}")
        cmd = [
            "yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format", "mp4", "-o", str(download_path), video_url
        ]
        try:
            subprocess.run(cmd, check=True)
            print(f"✅ Downloaded original: {download_path.name}")
        except Exception as e:
            print(f"❌ Download Error: {e}")
            return
    
    try:
        reveal_path = download_path
        segments_file = import_folder / f"{download_path.stem}_keep_segments.json"

        # Requirement 4: Skip process_with_gemini call if requested
        if api_key and not skip_api:
            segments_file = process_with_gemini(download_path)
            reveal_path = segments_file
        elif skip_api:
            print("⏭️ --skipAPI used: Skipping Gemini processing.")

        # Requirement 3: Skip apply_moviepy_cuts call if requested
        if segments_file and segments_file.exists() and not skip_edit:
            processed_video = apply_moviepy_cuts(download_path, segments_file)
            if processed_video:
                reveal_path = processed_video
        elif skip_edit:
            print("⏭️ --skipEditMovie used: Skipping MoviePy rendering.")

        # subprocess.run(["open", "-a", "iMovie"])
        subprocess.run(["open", "-R", str(reveal_path)])
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    download_and_open()