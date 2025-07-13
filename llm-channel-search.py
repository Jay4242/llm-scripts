import yt_dlp
import json
import sys
import subprocess
import os
import argparse
import re
import html2text

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
    vtt_dir = "vtt"
    if not os.path.exists(vtt_dir):
        os.makedirs(vtt_dir)

    output_path = os.path.join(vtt_dir, output_filename)

    ydl_opts = {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitlesformat': 'vtt',
        'subtitleslangs': ['en'],
        'outtmpl': output_path,
        'no_warnings': True,
        'quiet': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print(f"VTT subtitles downloaded to {output_path}.en.vtt")
    except yt_dlp.utils.DownloadError as e:
        print(f"Error downloading VTT subtitles for {url}: {e}")

def download_srv3_subtitles(url, output_filename):
    """Downloads srv3 subtitles from a YouTube video."""
    srv3_dir = "srv3"
    if not os.path.exists(srv3_dir):
        os.makedirs(srv3_dir)

    output_path = os.path.join(srv3_dir, output_filename)

    # Check if the srv3 file already exists
    if os.path.exists(f"{output_path}.en.srv3"):
        print(f"srv3 subtitles already exist for {output_filename}")
        return

    ydl_opts = {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitlesformat': 'srv3',
        'subtitleslangs': ['en'],
        'outtmpl': output_path,
        'no_warnings': True,
        'quiet': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print(f"srv3 subtitles downloaded to {output_path}.en.srv3")
    except yt_dlp.utils.DownloadError as e:
        print(f"Error downloading srv3 subtitles for {url}: {e}")


def search_channel(channel_url, search_query, llm_question=None):
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

                    subtitle_filename = os.path.join("vtt", f"{video_id}.en.vtt")

                    try:
                        with open(subtitle_filename, 'r', encoding='utf-8') as f:
                            subtitles_vtt = f.read()
                    except FileNotFoundError:
                        print(f"Subtitle file {subtitle_filename} not found.")
                        continue

                    if subtitles_vtt:
                        subtitles = parse_vtt(subtitles_vtt)
                        if subtitles:
                            matching_subs = []
                            for sub in subtitles:
                                if search_query.lower() in sub['text'].lower():
                                    matching_subs.append(sub)
                            
                            if matching_subs:
                                print(f"Match in: {video_url}")
                                for sub in matching_subs:
                                    print(f"  - {sub['timecode_line']}")
                                    print(f"  - {sub['text']}")
                                
                                if llm_question:
                                    download_srv3_subtitles(video_url, output_filename)
                                    srv3_filename = os.path.join("srv3", f"{video_id}.en.srv3")
                                    
                                    try:
                                        with open(srv3_filename, 'r', encoding='utf-8') as f:
                                            srv3_content = f.read()
                                        
                                        # Process srv3 with html2text
                                        h = html2text.HTML2Text()
                                        h.ignore_links = True
                                        clean_text = h.handle(srv3_content)
                                        
                                        # Overwrite the srv3 file with the cleaned text
                                        with open(srv3_filename, 'w', encoding='utf-8') as f:
                                            f.write(clean_text)

                                        command = [
                                            "/usr/local/bin/llm-python-file.py",
                                            srv3_filename,
                                            "You are a helpful assistant.",
                                            f"The following are subtitles from a youtube video that matched the query `{search_query}`. Please answer the user's question based on the full transcript.",
                                            llm_question,
                                            "0.0"
                                        ]
                                        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                                        stdout, stderr = process.communicate()

                                        if stderr:
                                            print(f"LLM Error: {stderr}")
                                        if stdout:
                                            print(f"LLM Response:\n{stdout}")

                                    except FileNotFoundError:
                                        print(f"SRV3 file {srv3_filename} not found.")
                                        continue
                                
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
    parser.add_argument("--llm", help="The question/command to be sent to the LLM over matching subtitles.")
    parser.add_argument("--download_vtt", action="store_true", help="Download VTT subtitles for the first video found.")


    args = parser.parse_args()

    channel_url = args.channel_url
    search_query = args.search_query
    llm_question = args.llm
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
                         output_filename = f"{first_video_id}"
                         download_vtt_subtitles(first_video_url, output_filename)
                    else:
                        print("Could not extract video ID from the first entry.")
                else:
                    print("No videos found in the channel.")
                sys.exit(0)  # Exit after downloading VTT subtitles
        except Exception as e:
            print(f"An error occurred while trying to download VTT subtitles: {e}")
            sys.exit(1)

    search_channel(channel_url, search_query, llm_question)
