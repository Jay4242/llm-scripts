#!/bin/bash

# Clear any existing files in /dev/shm/llm-video-analysis/
if [ -d /dev/shm/llm-video-analysis/ ]; then
  rm -rf /dev/shm/llm-video-analysis/*
fi

mkdir -p /dev/shm/llm-video-analysis/ || exit 1
temp_dir=/dev/shm/llm-video-analysis/

# Option to process all frames at once
all_frames=false

# Option to process by scene change
scene_change=false

# Scene change threshold
scene_threshold=0.3

# Option to download subtitles
subtitles=false

# Fixed frame rate
frame_rate=2

# Frames per batch
frames_per_batch=20

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -a|--all-frames)
      all_frames=true
      shift
      ;;
    -s|--scene-change)
      scene_change=true
      shift
      ;;
    -ss|--subtitles)
      subtitles=true
      shift
      ;;
    *)
      video_url=$1
      shift
      break
      ;;
  esac
done

# Check if video_url is empty
if [ -z "$video_url" ]; then
  echo "Usage: $0 [-a|--all-frames] [-s|--scene-change] [-ss|--subtitles] <video_url>"
  exit 1
fi

# Download the video and get the title
yt-dlp --no-warnings --cookies-from-browser chrome -q -f "bestvideo[height<=720]+bestaudio/best[height<=720]" -o "${temp_dir}/video.%(ext)s" "${video_url}" || exit 1
title=$(yt-dlp --no-warnings -q --cookies-from-browser chrome --get-title "${video_url}")
video="${temp_dir}/video.$(echo $(ls ${temp_dir}/video.* | cut -d '.' -f 2) )"

# Download subtitles if the option is enabled
if $subtitles; then
  # Try to download regular subtitles
  yt-dlp --no-warnings --cookies-from-browser chrome -q --write-subs --sub-format vtt -o "${temp_dir}/video.%(ext)s" "${video_url}" || {
    # If regular subtitles fail, try to download automatic subtitles
    yt-dlp --no-warnings --cookies-from-browser chrome -q --write-auto-subs --sub-format vtt -o "${temp_dir}/video.%(ext)s" "${video_url}" || echo "Subtitle download failed, continuing without subtitles."
  }
fi

# Extract frames from the video
if $scene_change; then
  # Extract scene frames with fixed frame rate
  ffmpeg -i "${video}" -vf "fps=${frame_rate},select='gt(scene,${scene_threshold})'" -vsync vfr "${temp_dir}/frame_%04d.jpg"
else
  # Extract frames at a fixed rate
  ffmpeg -i "${video}" -vf "fps=${frame_rate}" "${temp_dir}/frame_%04d.jpg"
fi

# Set the prompt
prompt="Describe what is happening in this series of images. The video title is: ${title}. Focus only on describing the visual elements present in the frames."

# Output file
output_file="${temp_dir}/analysis_output.txt"

# Clear the output file
> "$output_file"

# Determine which python script to use
if $subtitles; then
  python_script="llm-python-vision-multi-images-file.py"
  # Use find to locate the subtitle file
  subtitle_file=$(find "${temp_dir}" -name "*.vtt" -print -quit)
  if [ -z "$subtitle_file" ]; then
    echo "No subtitle file found, continuing without subtitles."
    python_script="llm-python-vision-multi-images.py"
  fi
else
  python_script="llm-python-vision-multi-images.py"
  subtitle_file=""
fi

# Process all frames at once
if $all_frames; then
  images=(${temp_dir}/frame_*.jpg)
  num_images=${#images[@]}

  # Calculate start and end times for the entire video
  start_time=0
  end_time=$(echo "($num_images / $frame_rate)" | bc)

  # Create a temporary subtitle file
  temp_subtitle_file="${temp_dir}/temp_subtitles.vtt"

  # Extract the subtitle snippet using ffmpeg
  ffmpeg -i "${subtitle_file}" -ss ${start_time} -to ${end_time} -c copy "${temp_subtitle_file}"

  # Check if the temp_subtitle_file has more than 2 lines
  if [ $(wc -l < "$temp_subtitle_file") -le 2 ]; then
    python_script="llm-python-vision-multi-images.py"
    rm -f "$temp_subtitle_file"
    temp_subtitle_file=""
  fi

  # Call llm-python-vision-multi-images.py with the prompt and all the image paths
  if $subtitles; then
    if [ -z "$temp_subtitle_file" ]; then
      output=$($python_script "$prompt" "${images[@]}")
    else
      output=$($python_script "$prompt" "$temp_subtitle_file" "${images[@]}")
      rm -f "$temp_subtitle_file"
    fi
  else
    output=$($python_script "$prompt" "${images[@]}")
  fi

  # Append the frame numbers and the output to the output file
  echo "Frames 1-${num_images}:" >> "$output_file"
  echo "$output" >> "$output_file"
else
  # Loop through the images in batches
  images=(${temp_dir}/frame_*.jpg)
  num_images=${#images[@]}

  for ((i=0; i<num_images; i+=$frames_per_batch)); do
    # Create a sub-array of images
    subset=("${images[@]:i:$frames_per_batch}")
    num_subset=${#subset[@]}

    # Get the starting and ending frame numbers
    start_frame=$((i + 1))
    end_frame=$((i + $num_subset))

    # Calculate the start and end times in seconds
    start_time=$(echo "($start_frame - 1) / $frame_rate" | bc)
    end_time=$(echo "$end_frame / $frame_rate" | bc)

    # Create a temporary subtitle file
    temp_subtitle_file="${temp_dir}/temp_subtitles.vtt"

    # Extract the subtitle snippet using ffmpeg
    ffmpeg -i "${subtitle_file}" -ss ${start_time} -to ${end_time} -c copy "${temp_subtitle_file}"

    # Check if the temp_subtitle_file has more than 2 lines
    if [ $(wc -l < "$temp_subtitle_file") -le 2 ]; then
      python_script="llm-python-vision-multi-images.py"
      rm -f "$temp_subtitle_file"
      temp_subtitle_file=""
    fi

    # Call llm-python-vision-multi-images.py with the prompt and the image paths
    if $subtitles; then
      if [ -z "$temp_subtitle_file" ]; then
        output=$($python_script "$prompt" "${subset[@]}")
      else
        output=$($python_script "$prompt" "$temp_subtitle_file" "${subset[@]}")
        rm -f "$temp_subtitle_file"
      fi
    else
      output=$($python_script "$prompt" "${subset[@]}")
    fi

    # Append the frame numbers and the output to the output file
    echo "Frames ${start_frame}-${end_frame}:" >> "$output_file"
    echo "$output" >> "$output_file"
  done
fi

# Summarize the output file using llm-python-file.py
system_prompt="You are a helpful assistant."
preprompt="The following is a summary of a series of frames of video ${title}:"
postprompt="Create one cohesive summarry of these events from the video"
temperature="0.7"

llm-python-file.py "$output_file" "$system_prompt" "$preprompt" "$postprompt" "$temperature"
