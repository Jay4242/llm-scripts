import yt_dlp
import json
import sys
import subprocess
import os
import argparse
import re

def parse_vtt(vtt_data):
    """Parses VTT data and returns a list of subtitle entries."""
    subtitles = []
    # Split the VTT data into individual cues
    lines = [line.strip() for line in vtt_data.strip().splitlines() if line.strip()]
    
    i = 0
    while i < len(lines):
        if "-->" in lines[i]:
            timecode_line = lines[i]
            text = ""
            i += 1
            while i < len(lines) and "-->" not in lines[i]:
                # Remove text within <> tags
                clean_line = re.sub(r'<[^>]+>', '', lines[i])
                text += clean_line + " "
                i += 1

            text = text.strip()

            # Extract start and end times from the timecode line
            try:
                start_time, end_time = timecode_line.split(' --> ')
                
                def to_seconds(time_str):
                    parts = time_str.split(':')
                    seconds = 0
                    if len(parts) == 3:  # HH:MM:SS.mmm
                        seconds += int(parts[0]) * 3600
                        seconds += int(parts[1]) * 60
                        seconds += float(parts[2].replace(',', '.'))
                    elif len(parts) == 2:  # MM:SS.mmm
                        seconds += int(parts[0]) * 60
                        seconds += float(parts[1].replace(',', '.'))
                    else:  # SS.mmm
                        seconds += float(parts[0].replace(',', '.'))
                    return seconds
                
                start = to_seconds(start_time)
                duration = to_seconds(end_time) - start
                
                subtitles.append({
                    'start': start,
                    'duration': duration,
                    'text': text,
                    'timecode_line': timecode_line  # Store the timecode line
                })
            except ValueError as e:
                print(f"Error parsing timecode line: {timecode_line} - {e}")
                continue
        else:
            i += 1  # Skip lines that are not timecode lines
            
    return subtitles

def get_automatic_subtitles(url):
    """
    Extracts automatic subtitles from a YouTube video and returns them as a string.
    Now downloads VTT format.

    Args:
        url: The URL of the YouTube video.

    Returns:
        The subtitles as a string, or None if an error occurred.
    """
    ydl_opts = {
        'skip_download': True,  # Skip downloading the video
        'writesubtitles': False,  # prevent writing to disk
        'writeautomaticsub': True,  # Download automatic subtitles
        'subtitlesformat': 'vtt',  # Set subtitle format to vtt
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

def download_vtt_subtitles(url, output_filename):
    """Downloads VTT subtitles from a YouTube video."""
    ydl_opts = {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitlesformat': 'vtt',
        'subtitleslangs': ['en'],
        'outtmpl': output_filename,
        'no_warnings': True,
        'quiet': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print(f"VTT subtitles downloaded to {output_filename}.en.vtt")
    except yt_dlp.utils.DownloadError as e:
        print(f"Error downloading VTT subtitles for {url}: {e}")

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
                    output_filename = f"{video_id}"
                    download_vtt_subtitles(video_url, output_filename)

                    subtitle_filename = f"{video_id}.en.vtt"

                    try:
                        with open(subtitle_filename, 'r', encoding='utf-8') as f:
                            subtitles_vtt = f.read()
                    except FileNotFoundError:
                        print(f"Subtitle file {subtitle_filename} not found.")
                        continue
                    finally:
                        f.close()

                    if subtitles_vtt:
                        subtitles = parse_vtt(subtitles_vtt)
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
                                        for sub in subtitles:
                                            if search_query.lower() in sub['text'].lower():
                                                print(f"  - {sub['timecode_line']}")  # Print the timecode line
                                                print(f"  - {sub['text']}")
                                        input("Press Enter to continue...")

                                else:
                                    # Simple grep-like search
                                    if search_query.lower() in all_text.lower():
                                        print(f"Grep Match: {video_url}")
                                        for sub in subtitles:
                                            if search_query.lower() in sub['text'].lower():
                                                print(f"  - {sub['timecode_line']}")  # Print the timecode line
                                                print(f"  - {sub['text']}")
                                        input("Press Enter to continue...")
    except Exception as e:
        print(f"An error occurred: {e}")
    except KeyboardInterrupt:
        print("\nExiting program.")
        sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search YouTube channel videos using subtitles.")
    parser.add_argument("channel_url", help="The YouTube channel URL (e.g., /@username/videos or /channel/CHANNEL_ID)")
    parser.add_argument("search_query", help="The search query.")
    parser.add_argument("--llm", action="store_true", help="Use LLM mode for searching (requires llm-python-file.py).")
    parser.add_argument("--download_vtt", action="store_true", help="Download VTT subtitles for the first video found.")


    args = parser.parse_args()

    channel_url = args.channel_url
    search_query = args.search_query
    llm_mode = args.llm
    download_vtt = args.download_vtt

    if download_vtt:
        # Extract the first video URL from the channel and download VTT subtitles
        ydl_opts = {
            'flat_playlist': True,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(channel_url, download=False)
                if 'entries' and len(info['entries']) > 0:
                    first_video_id = info['entries'][0].get('id')
                    if first_video_id:
                         first_video_url = f"https://www.youtube.com/watch?v={first_video_id}"
                         download_vtt_subtitles(first_video_url)
                    else:
                        print("Could not extract video ID from the first entry.")
                else:
                    print("No videos found in the channel.")
                sys.exit(0)  # Exit after downloading VTT subtitles
        except Exception as e:
            print(f"An error occurred while trying to download VTT subtitles: {e}")
            sys.exit(1)

    search_channel(channel_url, search_query, llm_mode)
