#!/bin/bash

# Clear any existing files in /dev/shm/llm-video-analysis/
rm -rf /dev/shm/llm-video-analysis/*

mkdir -p /dev/shm/llm-video-analysis/ || exit 1
temp_dir=/dev/shm/llm-video-analysis/
video_url=$1

# Download the video and get the title
yt-dlp --no-warnings -q -o "${temp_dir}/video.%(ext)s" "${video_url}" || exit 1
title=$(yt-dlp --no-warnings -q --get-title "${video_url}")
video="${temp_dir}/video.$(echo $(ls ${temp_dir}/video.* | cut -d '.' -f 2) )"

# Extract frames from the video
ffmpeg -i "${video}" -vf "fps=1" "${temp_dir}/frame_%04d.jpg"

# Set the prompt
prompt="Describe what is happening in this series of images. The video title is: ${title}"

# Output file
output_file="${temp_dir}/analysis_output.txt"

# Loop through the images in batches of 5
images=(${temp_dir}/frame_*.jpg)
num_images=${#images[@]}

# Clear the output file
> "$output_file"

for ((i=0; i<num_images; i+=5)); do
  # Create a sub-array of up to 5 images
  subset=("${images[@]:i:5}")

  # Call llm-python-vision-multi-images.py with the prompt and the image paths
  output=$(llm-python-vision-multi-images.py "$prompt" "${subset[@]}")

  # Append the output to the output file
  echo "$output" >> "$output_file"
done

# Summarize the output file using llm-python-file.py
system_prompt="You are a helpful assistant."
preprompt="The following is a summary of a series of frames of video:"
postprompt="Create one cohesive summarry of these events."
temperature="0.7"

llm-python-file.py "$output_file" "$system_prompt" "$preprompt" "$postprompt" "$temperature"
