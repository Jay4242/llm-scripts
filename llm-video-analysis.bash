#!/bin/bash

# Clear any existing files in /dev/shm/llm-video-analysis/
rm -rf /dev/shm/llm-video-analysis/*

mkdir -p /dev/shm/llm-video-analysis/ || exit 1
temp_dir=/dev/shm/llm-video-analysis/
video_url=$1

# Option to process all frames at once
all_frames=false

# Parse command-line arguments
while [[ $# -gt 1 ]]; do
  case "$1" in
    -a|--all-frames)
      all_frames=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

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

# Clear the output file
> "$output_file"

# Process all frames at once
if $all_frames; then
  images=(${temp_dir}/frame_*.jpg)
  num_images=${#images[@]}

  # Call llm-python-vision-multi-images.py with the prompt and all the image paths
  output=$(llm-python-vision-multi-images.py "$prompt" "${images[@]}")

  # Append the frame numbers and the output to the output file
  echo "Frames 1-${num_images}:" >> "$output_file"
  echo "$output" >> "$output_file"
else
  # Loop through the images in batches of 5
  images=(${temp_dir}/frame_*.jpg)
  num_images=${#images[@]}

  for ((i=0; i<num_images; i+=5)); do
    # Create a sub-array of up to 5 images
    subset=("${images[@]:i:5}")

    # Get the starting and ending frame numbers
    start_frame=$((i + 1))
    end_frame=$((i + ${#subset[@]}))

    # Call llm-python-vision-multi-images.py with the prompt and the image paths
    output=$(llm-python-vision-multi-images.py "$prompt" "${subset[@]}")

    # Append the frame numbers and the output to the output file
    echo "Frames ${start_frame}-${end_frame}:" >> "$output_file"
    echo "$output" >> "$output_file"
  done
fi

# Summarize the output file using llm-python-file.py
system_prompt="You are a helpful assistant."
preprompt="The following is a summary of a series of frames of video:"
postprompt="Create one cohesive summarry of these events."
temperature="0.7"

llm-python-file.py "$output_file" "$system_prompt" "$preprompt" "$postprompt" "$temperature"
