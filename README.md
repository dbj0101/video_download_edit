# video_download_edit

A Python-based automation tool that downloads videos via `yt-dlp`, analyzes speaker segments using the **Gemini 2.0 Flash API**, and performs surgical cuts using **MoviePy**.

## 🛠 Prerequisites

Ensure you have **Python 3.10+** and **FFmpeg** installed on your Mac. You can install FFmpeg via Homebrew:
```bash
brew install ffmpeg
```

## 📦 Installation

1. **Clone the repository** and navigate to the folder.

2. **Install dependencies** via pip:

```Bash
pip install moviepy yt-dlp google-generativeai python-dotenv
```
3. **Configure Environment:** Create a .env file in the root directory:

```Code snippet
GEMINI_API_KEY=your_api_key_here
FILE_PREFIX=VF_
INDEX_WAIT_TIME=60
# Optional: Set a custom prompt for the AI analysis
GEMINI_PROMPT="Include all of Laura speaking; only 1 second of Aaron."
```

## 🚀 Usage
The script uses an **opt-in** architecture. You must explicitly tell it which actions to perform.

1. **Download Only**
Downloads the video to the `/imported` folder using the current date as the filename.

```Bash
python3 import_video.py -u "https://youtube.com/watch?v=example"
```
2. **Download and Analyze** (Gemini API)
Downloads and generates a `keep_segments.json` file based on your AI prompt.

```Bash
python3 import_video.py -u "URL" --doAPI
```
3. **Full Automation (Download, Analyze, and Cut)**
The full "surgical cut" pipeline.

```Bash
python3 import_video.py -u "URL" --doAPI --doEdit
```
4. **Edit Existing File**
If the video and JSON already exist in /imported, you can skip the web/API steps:

```Bash
python3 import_video.py --doEdit
```
## 📝 Script Arguments
* `-u "URL" `: The video source URL.

* `--doAPI` : Triggers the Gemini 1.5/2.0 indexing and speaker analysis.

* `--doEdit` : Triggers the MoviePy rendering process to create the final cut.
