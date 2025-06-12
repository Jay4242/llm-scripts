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

# Option to use cookies from browser
use_cookies=false

# Option to skip title extraction
no_title=false

# Option for interactive prompting
interactive_prompt=false

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
    -c|--cookies)
      use_cookies=true
      shift
      ;;
    -nt|--no-title)
      no_title=true
      shift
      ;;
    -p|--prompt) # New flag for interactive prompting
      interactive_prompt=true
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
  echo "Usage: $0 [-a|--all-frames] [-s|--scene-change] [-ss|--subtitles] [-c|--cookies] [-nt|--no-title] [-p|--prompt] <video_url>"
  exit 1
fi

# Construct the cookies option for yt-dlp
cookies_option=""
if $use_cookies; then
  cookies_option="--cookies-from-browser chrome"
fi

# Download the video
yt-dlp --no-warnings ${cookies_option} -q -f "bestvideo[height<=720]+bestaudio/best[height<=720]" -o "${temp_dir}/video.%(ext)s" "${video_url}" || exit 1
video="${temp_dir}/video.$(echo $(ls ${temp_dir}/video.* | cut -d '.' -f 2) )"

# Get the video title if not skipped
title=""
if ! $no_title; then
  extracted_title=$(yt-dlp --no-warnings -q ${cookies_option} --get-title "${video_url}")
  if [ -n "$extracted_title" ]; then
    title="$extracted_title"
  fi
fi

# Download subtitles if the option is enabled
subtitle_file=""
if $subtitles; then
  # Try to download regular subtitles
  yt-dlp --no-warnings ${cookies_option} -q --write-subs --sub-format vtt -o "${temp_dir}/video.%(ext)s" "${video_url}" || {
    # If regular subtitles fail, try to download automatic subtitles
    yt-dlp --no-warnings ${cookies_option} -q --write-auto-subs --sub-format vtt -o "${temp_dir}/video.%(ext)s" "${video_url}" || echo "Subtitle download failed, continuing without subtitles."
  }
  # Use find to locate the subtitle file
  subtitle_file=$(find "${temp_dir}" -name "*.vtt" -print -quit)
  if [ -z "$subtitle_file" ]; then
    echo "No subtitle file found, continuing without subtitles."
    # If no subtitle file is found, effectively disable subtitle processing for the rest of the script
    subtitles=false
  fi
fi

# Extract frames from the video
if $scene_change; then
  # Extract scene frames with fixed frame rate
  ffmpeg -i "${video}" -vf "fps=${frame_rate},select='gt(scene,${scene_threshold})'" -vsync vfr "${temp_dir}/frame_%04d.jpg"
else
  # Extract frames at a fixed rate
  ffmpeg -i "${video}" -vf "fps=${frame_rate}" "${temp_dir}/frame_%04d.jpg"
fi

# Define summarization prompts and temperature
system_prompt="You are a helpful assistant."
temperature="0.7"

# Set the base visual description prompt
visual_description_prompt_base="Describe what is happening in this series of images."
if [ -n "$title" ]; then
  visual_description_prompt_base+=" The video title is: ${title}."
fi
visual_description_prompt_base+=" Focus only on describing the visual elements present in the frames."

# Output file
output_file="${temp_dir}/analysis_output.txt"

# --- Start of conditional logic for interactive vs. non-interactive mode ---

if $interactive_prompt; then
  preprompt="The following are frames from a video"
  while true; do
    echo -n "Enter your prompt (or 'quit'/'exit' or blank line to finish): "
    read -r user_postprompt
    user_postprompt=$(echo "$user_postprompt" | xargs) # Trim whitespace

    if [[ -z "$user_postprompt" || "$user_postprompt" == "quit" || "$user_postprompt" == "exit" ]]; then
      echo "Exiting interactive prompt."
      break
    fi
    postprompt="$user_postprompt"

    # Clear the output file for each new prompt
    > "$output_file"

    # Determine the final prompt based on --all-frames and the current postprompt
    if $all_frames; then
      prompt="${preprompt} ${visual_description_prompt_base} ${postprompt}"
    else
      # When not --all-frames, use the standard visual description prompt for individual batches
      # The postprompt will be used in the final summarization step.
      prompt="${visual_description_prompt_base}"
    fi

    # Process all frames at once (if --all-frames)
    if $all_frames; then
      images=(${temp_dir}/frame_*.jpg)
      num_images=${#images[@]}

      # Calculate start and end times for the entire video
      start_time=0
      end_time=$(echo "($num_images / $frame_rate)" | bc)

      current_python_script="llm-python-vision-multi-images.py" # Default script
      current_subtitle_arg=""
      temp_subtitle_file="" # Initialize to empty

      if $subtitles && [ -n "$subtitle_file" ]; then # Only proceed if subtitles are enabled and a main subtitle file was found
        temp_subtitle_file="${temp_dir}/temp_subtitles.vtt"
        ffmpeg -i "${subtitle_file}" -ss ${start_time} -to ${end_time} -c copy "${temp_subtitle_file}" 2>/dev/null

        # Check if the temp_subtitle_file exists and has content (more than 2 lines for VTT header)
        if [ -s "$temp_subtitle_file" ] && [ $(wc -l < "$temp_subtitle_file") -gt 2 ]; then
          current_subtitle_arg="$temp_subtitle_file"
          current_python_script="llm-python-vision-multi-images-file.py"
        else
          # If temp subtitle file is empty or failed, revert to the non-file script
          rm -f "$temp_subtitle_file" # Clean up if it was created but empty
          temp_subtitle_file="" # Ensure it's empty for cleanup later
        fi
      fi

      # Construct the command arguments
      cmd_args=("$prompt") # Use the conditionally set 'prompt'
      if [ -n "$current_subtitle_arg" ]; then
        cmd_args+=("$current_subtitle_arg")
      fi
      cmd_args+=("${images[@]}")

      echo "Sending frames 1-${num_images} to LLM..." >&2 # Debugging output

      # Call the appropriate python script
      output=$($current_python_script "${cmd_args[@]}")

      # Append the frame numbers and the output to the output file
      echo "Frames 1-${num_images}:" >> "$output_file"
      echo "$output" >> "$output_file"

      # Clean up temporary subtitle file if it was created
      if [ -n "$temp_subtitle_file" ]; then
        rm -f "$temp_subtitle_file"
      fi

    else # This is the original batch processing logic
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

        current_python_script="llm-python-vision-multi-images.py" # Default script
        current_subtitle_arg=""
        temp_subtitle_file="" # Initialize to empty

        if $subtitles && [ -n "$subtitle_file" ]; then # Only proceed if subtitles are enabled and a main subtitle file was found
          temp_subtitle_file="${temp_dir}/temp_subtitles.vtt"
          ffmpeg -i "${subtitle_file}" -ss ${start_time} -to ${end_time} -c copy "${temp_subtitle_file}" 2>/dev/null

          # Check if the temp_subtitle_file exists and has content (more than 2 lines for VTT header)
          if [ -s "$temp_subtitle_file" ] && [ $(wc -l < "$temp_subtitle_file") -gt 2 ]; then
            current_subtitle_arg="$temp_subtitle_file"
            current_python_script="llm-python-vision-multi-images-file.py"
          else
            rm -f "$temp_subtitle_file"
            temp_subtitle_file=""
          fi
        fi

        # Construct the command arguments
        cmd_args=("$prompt") # Use the conditionally set 'prompt'
        if [ -n "$current_subtitle_arg" ]; then
          cmd_args+=("$current_subtitle_arg")
        fi
        cmd_args+=("${subset[@]}")

        echo "Sending frames ${start_frame}-${end_frame} to LLM..." >&2 # Debugging output

        # Call the appropriate python script
        output=$($current_python_script "${cmd_args[@]}")

        # Append the frame numbers and the output to the output file
        echo "Frames ${start_frame}-${end_frame}:" >> "$output_file"
        echo "$output" >> "$output_file"

        # Clean up temporary subtitle file if it was created
        if [ -n "$temp_subtitle_file" ]; then
          rm -f "$temp_subtitle_file"
        fi
      done
    fi

    # Summarize the output file using llm-python-file.py (only if not --all-frames)
    if ! $all_frames; then
      llm-python-file.py "$output_file" "$system_prompt" "$preprompt" "$postprompt" "$temperature"
    fi
    echo "" # Add a newline for better readability between prompts
  done # End of while true loop for interactive prompt
else # Original non-interactive processing
  # Define preprompt and postprompt for non-interactive mode
  preprompt="The following is a summary of a series of frames of video"
  if [ -n "$title" ]; then
    preprompt+=" ${title}:"
  else
    preprompt+=":"
  fi
  postprompt="Create one cohesive summary of these events from the video"

  # Determine the final prompt based on --all-frames
  if $all_frames; then
    # When --all-frames is used, combine summarization prompts with the visual description
    # The system prompt is handled by the python script, so we only combine user-facing parts.
    prompt="${preprompt} ${visual_description_prompt_base} ${postprompt}"
  else
    # When not --all-frames, use the standard visual description prompt
    prompt="${visual_description_prompt_base}"
  fi

  # Clear the output file (only once for non-interactive mode)
  > "$output_file"

  # Process all frames at once
  if $all_frames; then
    images=(${temp_dir}/frame_*.jpg)
    num_images=${#images[@]}

    # Calculate start and end times for the entire video
    start_time=0
    end_time=$(echo "($num_images / $frame_rate)" | bc)

    current_python_script="llm-python-vision-multi-images.py" # Default script
    current_subtitle_arg=""
    temp_subtitle_file="" # Initialize to empty

    if $subtitles && [ -n "$subtitle_file" ]; then # Only proceed if subtitles are enabled and a main subtitle file was found
      temp_subtitle_file="${temp_dir}/temp_subtitles.vtt"
      ffmpeg -i "${subtitle_file}" -ss ${start_time} -to ${end_time} -c copy "${temp_subtitle_file}" 2>/dev/null

      # Check if the temp_subtitle_file exists and has content (more than 2 lines for VTT header)
      if [ -s "$temp_subtitle_file" ] && [ $(wc -l < "$temp_subtitle_file") -gt 2 ]; then
        current_subtitle_arg="$temp_subtitle_file"
        current_python_script="llm-python-vision-multi-images-file.py"
      else
        # If temp subtitle file is empty or failed, revert to the non-file script
        rm -f "$temp_subtitle_file" # Clean up if it was created but empty
        temp_subtitle_file="" # Ensure it's empty for cleanup later
      fi
    fi

    # Construct the command arguments
    cmd_args=("$prompt") # Use the conditionally set 'prompt'
    if [ -n "$current_subtitle_arg" ]; then
      cmd_args+=("$current_subtitle_arg")
    fi
    cmd_args+=("${images[@]}")

    echo "Sending frames 1-${num_images} to LLM..." >&2 # Debugging output

    # Call the appropriate python script
    output=$($current_python_script "${cmd_args[@]}")

    # Append the frame numbers and the output to the output file
    echo "Frames 1-${num_images}:" >> "$output_file"
    echo "$output" >> "$output_file"

    # Clean up temporary subtitle file if it was created
    if [ -n "$temp_subtitle_file" ]; then
      rm -f "$temp_subtitle_file"
    fi

  else # This is the original batch processing logic
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

      current_python_script="llm-python-vision-multi-images.py" # Default script
      current_subtitle_arg=""
      temp_subtitle_file="" # Initialize to empty

      if $subtitles && [ -n "$subtitle_file" ]; then # Only proceed if subtitles are enabled and a main subtitle file was found
        temp_subtitle_file="${temp_dir}/temp_subtitles.vtt"
        ffmpeg -i "${subtitle_file}" -ss ${start_time} -to ${end_time} -c copy "${temp_subtitle_file}" 2>/dev/null

        # Check if the temp_subtitle_file exists and has content (more than 2 lines for VTT header)
        if [ -s "$temp_subtitle_file" ] && [ $(wc -l < "$temp_subtitle_file") -gt 2 ]; then
          current_subtitle_arg="$temp_subtitle_file"
          current_python_script="llm-python-vision-multi-images-file.py"
        else
          rm -f "$temp_subtitle_file"
          temp_subtitle_file=""
        fi
      fi

      # Construct the command arguments
      cmd_args=("$prompt") # Use the conditionally set 'prompt'
      if [ -n "$current_subtitle_arg" ]; then
        cmd_args+=("$current_subtitle_arg")
      fi
      cmd_args+=("${subset[@]}")

      echo "Sending frames ${start_frame}-${end_frame} to LLM..." >&2 # Debugging output

      # Call the appropriate python script
      output=$($current_python_script "${cmd_args[@]}")

      # Append the frame numbers and the output to the output file
      echo "Frames ${start_frame}-${end_frame}:" >> "$output_file"
      echo "$output" >> "$output_file"

      # Clean up temporary subtitle file if it was created
      if [ -n "$temp_subtitle_file" ]; then
        rm -f "$temp_subtitle_file"
      fi
    done
  fi

  # Summarize the output file using llm-python-file.py (only if not --all-frames)
  if ! $all_frames; then
    llm-python-file.py "$output_file" "$system_prompt" "$preprompt" "$postprompt" "$temperature"
  fi
fi # End of conditional logic for interactive vs. non-interactive mode
