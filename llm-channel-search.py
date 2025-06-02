import yt_dlp
import json
import sys
import subprocess
import os
import argparse

def parse_srv3(srv3_data):
    """Parses srv3 data and returns a list of subtitle entries."""
    try:
        data = json.loads(srv3_data)
        events = data.get('events', [])
        subtitles = []
        for event in events:
            start_ms = event.get('tStartMs', 0)
            duration_ms = event.get('dDurationMs', 0)
            segs = event.get('segs', [])
            # Join the segments, strip whitespace, and filter out empty lines
            text = ' '.join(s.strip() for s in (seg.get('utf8', '') for seg in segs) if s.strip())
            subtitles.append({
                'start': start_ms / 1000.0,
                'duration': duration_ms / 1000.0,
                'text': text
            })
        return subtitles
    except json.JSONDecodeError:
        print("Error decoding srv3 data.")
        return []

def get_automatic_subtitles(url):
    """
    Extracts automatic subtitles from a YouTube video and returns them as a string.

    Args:
        url: The URL of the YouTube video.

    Returns:
        The subtitles as a string, or None if an error occurred.
    """
    ydl_opts = {
        'skip_download': True,  # Skip downloading the video
        'writesubtitles': False,  # prevent writing to disk
        'writeautomaticsub': True,  # Download automatic subtitles
        'subtitlesformat': 'srv3',  # Set subtitle format to srv3
        'outtmpl': '%(title)s-%(id)s.%(ext)s',  # Output filename template (not actually used)
        'no_warnings': True,  # Suppress warnings
        'quiet': True,  # Activate quiet mode
        'subtitleslangs': ['en'], # only get english subs
        'allsubtitles': False,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            if 'subtitles' in info_dict and 'en' in info_dict['subtitles']:
                sub_info = info_dict['subtitles']['en'][0]
                # Download the subtitle data
                sub_data = ydl.urlopen(sub_info['url']).read().decode('utf-8')
                return sub_data
            elif 'automatic_captions' in info_dict and 'en' in info_dict['automatic_captions']:
                sub_info = info_dict['automatic_captions']['en'][0]
                sub_data = ydl.urlopen(sub_info['url']).read().decode('utf-8')
                return sub_data
            else:
                return "No English automatic subtitles found."
    except yt_dlp.utils.DownloadError as e:
        print(f"Error downloading subtitles for {url}: {e}")
        return None

def search_channel(channel_url, search_query, llm_mode=False):
    """Searches a YouTube channel for videos related to the search query."""
    try:
        ydl_opts = {
            'flat_playlist': True,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            if 'entries' not in info:
                print(f"Could not extract playlist entries from {channel_url}")
                return

            for entry in info['entries']:
                if entry and 'id' in entry:
                    video_id = entry['id']
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    subtitles_srv3 = get_automatic_subtitles(video_url)

                    if subtitles_srv3:
                        subtitles = parse_srv3(subtitles_srv3)
                        if subtitles:
                            all_text = "\n".join([entry['text'] for entry in subtitles if entry['text'].strip()])
                            if all_text:
                                if llm_mode:
                                    # Use llm-python-file.py to check relevance
                                    command = [
                                        "/usr/local/bin/llm-python-file.py",
                                        "-",  # Read from stdin
                                        "You are a helpful assistant.",
                                        f"The following is a youtube video transcription.",
                                        f"Does this help answer the question or topic of `{search_query}`? Start your answer with `Yes` or `No`.",
                                        "0.0"
                                    ]
                                    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                                    stdout, stderr = process.communicate(input=all_text)
                                    if "Yes" in stdout:
                                        print(f"LLM Match: {video_url}")
                                else:
                                    # Simple grep-like search
                                    if search_query.lower() in all_text.lower():
                                        print(f"Grep Match: {video_url}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search YouTube channel videos using subtitles.")
    parser.add_argument("channel_url", help="The YouTube channel URL (e.g., /@username/videos or /channel/CHANNEL_ID)")
    parser.add_argument("search_query", help="The search query.")
    parser.add_argument("--llm", action="store_true", help="Use LLM mode for searching (requires llm-python-file.py).")

    args = parser.parse_args()

    channel_url = args.channel_url
    search_query = args.search_query
    llm_mode = args.llm

    search_channel(channel_url, search_query, llm_mode)
