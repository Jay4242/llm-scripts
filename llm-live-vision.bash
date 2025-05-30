#!/bin/bash

# Set the initial prompt for the image description
prompt="Describe what you see in the image."

# Loop indefinitely, running the image processing and description steps
while sleep 1 ; do
  # Use ffmpeg to extract a single frame from a video URL copied from the clipboard
  # The video URL is obtained using yt-dlp
  # The frame is saved as /dev/shm/output.jpg
  ffmpeg -v quiet -y -i $(yt-dlp -g "$(xclip -o -selection clipboard)") -frames:v 1 -q:v 3 /dev/shm/output.jpg && \
  # Use llm-python-vision.py to analyze the image and generate a text description based on the prompt
  # The output is piped to tee to save it to /dev/shm/output.txt and also pass it to the next command
  llm-python-vision-ollama.py /dev/shm/output.jpg "${prompt}" | tee /dev/shm/output.txt
  # Open the image in ristretto
  ristretto /dev/shm/output.jpg &
  # Store the process ID of ristretto
  let pid=$!
  # Use espeak to speak the text description from /dev/shm/output.txt
  espeak < <(cat /dev/shm/output.txt)
  # Kill the ristretto process
  kill -- "$pid"
done
