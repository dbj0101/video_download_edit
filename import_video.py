import subprocess
import os
import sys
import time
import json
import argparse
from pathlib import Path
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv
from moviepy import VideoFileClip, concatenate_videoclips

# 1. Load the .env file
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
env_prompt = os.getenv("GEMINI_PROMPT")
FILE_PREFIX = os.getenv("FILE_PREFIX", "VF_") 
INDEX_WAIT_TIME = int(os.getenv("INDEX_WAIT_TIME", "60"))

if api_key:
    genai.configure(api_key=api_key)

def countdown_sleep(seconds, message):
    """Writes a countdown on one line that gets replaced."""
    for i in range(seconds, 0, -1):
        print(f"\r{message} in {i}s...   ", end="", flush=True)
        time.sleep(1)
    print(f"\r{message}... COMPLETE!          ")

def process_with_gemini(video_path):
    # Uses the custom prompt from your session for Laura/Aaron logic
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
        countdown_sleep(INDEX_WAIT_TIME, "⏳ Gemini is indexing video frames")
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

def main():
    parser = argparse.ArgumentParser(description="Video Download and Auto-Editor")
    parser.add_argument("-u", "--url", help="URL of the video to download")
    parser.add_argument("--doAPI", action="store_true", help="Run Gemini API analysis")
    parser.add_argument("--doEdit", action="store_true", help="Run MoviePy editing/rendering")
    
    args = parser.parse_args()

    today_str = datetime.now().strftime("%Y%m%d")
    filename = f"{FILE_PREFIX}{today_str}.mp4" 

    current_dir = Path(__file__).parent
    import_folder = current_dir / "imported"
    import_folder.mkdir(exist_ok=True)
    video_path = import_folder / filename

    # 1. Handle Download
    if args.url:
        if video_path.exists():
            print(f"📂 Video already exists: {video_path.name}. Skipping download.")
        else:
            print(f"🌐 Downloading: {args.url}")
            cmd = [
                "yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "--merge-output-format", "mp4", "-o", str(video_path), args.url
            ]
            try:
                subprocess.run(cmd, check=True)
                print(f"✅ Downloaded original: {video_path.name}")
            except Exception as e:
                print(f"❌ Download Error: {e}")
                return
    else:
        print("⏭️ No URL provided: Skipping download step.")

    # 2. Check if video exists before continuing
    if not video_path.exists():
        print(f"❌ Error: {video_path.name} not found. Use -u to download or place file in /imported.")
        return

    reveal_path = video_path
    segments_file = import_folder / f"{video_path.stem}_keep_segments.json"

    # 3. Handle API Analysis
    if args.doAPI:
        if api_key:
            segments_file = process_with_gemini(video_path)
            if segments_file:
                reveal_path = segments_file
        else:
            print("❌ GEMINI_API_KEY not found in .env")
    else:
        print("⏭️ --doAPI not used: Skipping Gemini processing.")

    # 4. Handle MoviePy Editing
    if args.doEdit:
        if segments_file and segments_file.exists():
            processed_video = apply_moviepy_cuts(video_path, segments_file)
            if processed_video:
                reveal_path = processed_video
        else:
            print(f"❌ Cannot edit: {segments_file.name} missing. Run with --doAPI first.")
    else:
        print("⏭️ --doEdit not used: Skipping MoviePy rendering.")

    # Final Step: Reveal in Finder
    subprocess.run(["open", "-R", str(reveal_path)])

if __name__ == "__main__":
    main()