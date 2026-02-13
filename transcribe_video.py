#!/usr/bin/env python3

import os
import sys
import subprocess
import tempfile
import requests
import argparse

def transcribe_video(video_path, translate=False, server_url="http://localhost:9191/inference"):
    """
    Transcribes a video file using a whisper.cpp server.

    Args:
        video_path (str): The path to the video file.
        translate (bool): Whether to request translation to English.
        server_url (str): The URL of the whisper.cpp server's inference endpoint.
    """
    if not os.path.exists(video_path):
        print(f"Error: Video file not found at '{video_path}'")
        return

    print(f"Processing video: {video_path}")
    if translate:
        print("Translation to English requested.")

    # 1. Extract audio and convert to 16kHz mono WAV using ffmpeg
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav_file:
        tmp_wav_path = tmp_wav_file.name
    
    try:
        print("Extracting audio with ffmpeg...")
        command = [
            "ffmpeg",
            "-i", video_path,
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            "-y",
            "-loglevel", "error",
            tmp_wav_path
        ]
        
        # Capture ffmpeg output and ignore decoding errors
        result = subprocess.run(command, check=True, capture_output=True, text=True, errors="ignore")

    except FileNotFoundError:
        print("Error: 'ffmpeg' not found. Please make sure it is installed and in your system's PATH.")
        os.remove(tmp_wav_path)
        return
    except subprocess.CalledProcessError as e:
        print("Error during ffmpeg audio extraction:")
        print(e.stderr)
        os.remove(tmp_wav_path)
        return

    # 2. Send audio to whisper-server
    try:
        print(f"Sending audio to whisper server at {server_url}...")
        with open(tmp_wav_path, "rb") as audio_file:
            files = {"file": (os.path.basename(tmp_wav_path), audio_file, "audio/wav")}
            params = {"response_format": "srt"}
            if translate:
                params["translate"] = "true"
            
            response = requests.post(server_url, files=files, data=params, timeout=3600) # 1 hour timeout
            response.raise_for_status()

    except requests.exceptions.RequestException as e:
        print(f"Error sending request to whisper server: {e}")
        return
    finally:
        # 4. Clean up temporary WAV file
        print("Cleaning up temporary audio file...")
        os.remove(tmp_wav_path)

    # 3. Save response to SRT file
    srt_path = os.path.splitext(video_path)[0] + ".srt"
    try:
        with open(srt_path, "w", encoding="utf-8") as srt_file:
            srt_file.write(response.text)
        print(f"Successfully created SRT file: {srt_path}")
    except IOError as e:
        print(f"Error writing SRT file: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transcribe a video file using a whisper.cpp server.")
    parser.add_argument("video_path", help="The path to the video file.")
    parser.add_argument("--translate", action="store_true", help="Request translation to English.")
    
    args = parser.parse_args()

    transcribe_video(args.video_path, args.translate)
