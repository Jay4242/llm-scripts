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

# Option to generate subtitles via transcription
transcribe=false

# Fixed frame rate
frame_rate=2
bc_scale=2

# -------------------------------------------------
# Helper: prepare a temporary subtitle segment for a given time range.
# Returns the path to a temporary subtitle file if it contains usable content,
# otherwise returns an empty string.
prepare_subtitles() {
    local start_time=$1
    local end_time=$2
    local src_file=$3
    local tmp_file="${temp_dir}/temp_subtitles_${start_time}_${end_time}.vtt"

    # Extract the subtitle segment; suppress non‑error output.
    ffmpeg -loglevel error -i "$src_file" -ss "$start_time" -to "$end_time" -c copy "$tmp_file"

    # Verify that the file exists and has more than just the VTT header.
    if [ -s "$tmp_file" ] && [ "$(wc -l < "$tmp_file")" -gt 2 ]; then
        echo "$tmp_file"
    else
        rm -f "$tmp_file"
        echo ""
    fi
}

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
    -t|--transcribe)
      transcribe=true
      shift
      ;;
    -p|--prompt) # New flag for interactive prompting
      interactive_prompt=true
      shift
      ;;
    -f|--fps) # New flag to set frames per second
      frame_rate=$2
      shift
      shift
      ;;
    -h|--help)
      cat <<'EOF'
Usage: $0 [options] <video_url>

Options:
  -a, --all-frames        Process all extracted frames in a single batch.
  -s, --scene-change      Detect scene changes and extract only those frames.
  -ss, --subtitles        Download and include subtitles (VTT) if available.
  -c, --cookies           Use cookies from Chrome for authenticated video sites.
  -nt, --no-title         Skip extracting the video title.
  -p, --prompt            Enable interactive prompting mode.
  -f, --fps <fps>         Set the frame extraction rate (default: 2 fps).
  -h, --help              Show this help message and exit.

Provide the video URL as the final argument.
EOF
      exit 0
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
  echo "Usage: $0 [-a|--all-frames] [-s|--scene-change] [-ss|--subtitles] [-c|--cookies] [-nt|--no-title] [-p|--prompt] [-f|--fps <fps>] [-h|--help] <video_url>"
  exit 1
fi

# Construct the cookies option for yt-dlp
cookies_option=""
if $use_cookies; then
  cookies_option="--cookies-from-browser chrome"
fi

# Determine if input is a local file or a URL
if [[ -f "$video_url" ]]; then
  video="$video_url"
else
  # Download the video
  yt-dlp --no-warnings ${cookies_option} -q -f "bestvideo[height<=720]+bestaudio/best[height<=720]" -o "${temp_dir}/video.%(ext)s" "${video_url}" || exit 1
  video="${temp_dir}/video.$(echo $(ls ${temp_dir}/video.* | cut -d '.' -f 2) )"
fi

# If transcribe option is enabled, generate subtitles using transcribe_video.py
if $transcribe; then
  echo "Transcribing video to generate subtitles..."
  /usr/local/bin/transcribe_video.py "$video"
  generated_srt="${video%.*}.srt"
  if [[ -f "$generated_srt" ]]; then
    cleaned_sub="${temp_dir}/clean_subtitle.txt"
    awk 'NF && $0 !~ /^[0-9]+$/ && $0 !~ /-->/ {print}' "$generated_srt" > "$cleaned_sub"
    subtitle_file="$cleaned_sub"
    echo "Cleaned subtitles prepared: $subtitle_file"
  else
    echo "Transcription failed: no subtitle file generated."
  fi
fi

# Get the video title if not skipped
title=""
if ! $no_title; then
  if [[ -f "$video_url" ]]; then
    title="${video_url##*/}"
  else
    extracted_title=$(yt-dlp --no-warnings -q ${cookies_option} --get-title "${video_url}")
    if [ -n "$extracted_title" ]; then
      title="$extracted_title"
    fi
  fi
fi

# Download subtitles if the option is enabled
subtitle_file=""
if $subtitles && [ -z "$subtitle_file" ] && ! [[ -f "$video_url" ]]; then
  # Attempt to download automatic English subtitles (VTT)
  yt-dlp --no-warnings ${cookies_option} -q --write-auto-subs --sub-format vtt --sub-lang "en" -o "${temp_dir}/video.%(ext)s" "${video_url}" || {
    echo "Automatic subtitle download failed, continuing without subtitles."
    subtitles=false
  }

  # Locate the downloaded subtitle file (any .vtt)
  echo "Debug: searching for subtitle files in ${temp_dir}"
  subtitle_file=$(find "${temp_dir}" -type f -iname "*.vtt" -print -quit)

  if [ -z "$subtitle_file" ]; then
    echo "No subtitle file found, continuing without subtitles."
    subtitles=false
  else
    echo "Subtitle file detected: $subtitle_file"
    # Clean subtitle file to remove <c> tags and their content
    clean_subtitle="${temp_dir}/clean_subtitle.vtt"

    awk '
      BEGIN {FS=OFS=""}
      # Keep header (including the blank line after Language)
      /^WEBVTT/ {print; next}
      # Blank lines containing <c> tags (replace with empty line)
      /<c>/ {print ""; next}
      # Process timestamp lines: keep only cues that have subtitle text.
      # After each cue, output two blank lines to separate from the next timestamp.
      /^[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3} --> /{
          timestamp=$0
          # Look ahead to the first line after the timestamp
          if (getline line) {
              if (line ~ /^[[:space:]]*$/) {
                  # No subtitle text – skip this cue entirely
                  next
              } else {
                  print timestamp
                  # Blank out subtitle line if it contains <c> tags
                  if (line ~ /<c>/) {
                      print ""
                  } else {
                      print line
                  }
                  # Print any additional subtitle lines until a blank line or next timestamp
                  while (getline line) {
                      if (line ~ /^[[:space:]]*$/) break
                      if (line ~ /^[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3} --> /) {
                          # Encountered next timestamp; push it back for the outer loop
                          $0=line
                          break
                      }
                      # Blank out lines containing <c> tags
                      if (line ~ /<c>/) {
                          print ""
                      } else {
                          print line
                      }
                  }
                  # Ensure two blank lines after each cue
                  print ""
                  print ""
              }
          }
          next
      }
      # Print all other lines (including blank lines) to keep spacing
      {print}
    ' "$subtitle_file" > "$clean_subtitle"
    subtitle_file="$clean_subtitle"
    echo "Cleaned subtitle file prepared: $subtitle_file"
  fi

  # Optional pause for debugging
  # read -p "Subtitle download step completed. Press Enter to continue..."
fi

# Extract frames from the video
if $scene_change; then
  # Extract scene frames with fixed frame rate
  ffmpeg -i "${video}" -vf "fps=${frame_rate},select='gt(scene,${scene_threshold})'" -vsync vfr -q:v 0 "${temp_dir}/frame_%08d.jpg"

  # Rename extracted frames with their presentation timestamp (pts_time)
  for frame_path in "${temp_dir}"/frame_*.jpg; do
    pts=${frame_path##*/frame_}
    pts=${pts%.jpg}
    pts_time=$(printf "%.3f" "$(bc -l <<< "$pts/16000")")
    if [[ -n "$pts_time" ]]; then
      new_name=$(printf "frame_%.3f.jpg" "$pts_time")
      mv "$frame_path" "$temp_dir/$new_name"
    else
      echo "Warning: Could not determine pts_time for $frame_path"
    fi
  done
else
  # Extract frames at a fixed rate
  ffmpeg -i "${video}" -vf "fps=${frame_rate}" -q:v 0 "${temp_dir}/frame_%08d.jpg"

  # Rename extracted frames with their presentation timestamp (pts_time)
  for frame_path in "${temp_dir}"/frame_*.jpg; do
    pts=${frame_path##*/frame_}
    pts=${pts%.jpg}
    pts_time=$(printf "%.3f" "$(bc -l <<< "$pts/16000")")
    if [[ -n "$pts_time" ]]; then
      new_name=$(printf "frame_%.3f.jpg" "$pts_time")
      mv "$frame_path" "$temp_dir/$new_name"
    else
      echo "Warning: Could not determine pts_time for $frame_path"
    fi
  done
fi

# Define summarization prompts and temperature
system_prompt="You are a helpful AI assistant that can analyse video frames and subtitles, then produce a concise, human-readable summary."
temperature="0.7" # Already defined, but explicitly used now

# Set the base visual description prompt
visual_description_prompt_base="For each supplied frame, describe the visible scene in 1-2 short sentences. Mention key objects, actions, settings, and any on-screen text. Do not speculate beyond what is shown. If a video title is known, keep it in mind but do not repeat it verbatim."

# Output file
output_file="${temp_dir}/analysis_output.txt"

# --- Start of conditional logic for interactive vs. non-interactive mode ---

if $interactive_prompt; then
  preprompt="You are looking at a set of extracted frames from a video."
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
      end_time=$(echo "scale=$bc_scale; ($num_images / $frame_rate)" | bc)

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
      cmd_args=("$prompt" "$temperature") # Prompt is sys.argv[1], Temperature is sys.argv[2]
      if [ -n "$current_subtitle_arg" ]; then
        cmd_args+=("$current_subtitle_arg") # Subtitle is sys.argv[3] for file script
      fi
      cmd_args+=("${images[@]}") # Images start at sys.argv[3] for non-file script, sys.argv[4] for file script

      echo "Sending frames 1-${num_images} to LLM..." >&2 # Debugging output

      # Call the appropriate python script and time it
      output=$(time -p $current_python_script "${cmd_args[@]}")

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
        start_time=$(echo "scale=$bc_scale; ($start_frame - 1) / $frame_rate" | bc)
        end_time=$(echo "scale=$bc_scale; $end_frame / $frame_rate" | bc)

        current_python_script="llm-python-vision-multi-images.py" # Default script
        current_subtitle_arg=""
        temp_subtitle_file="" # Initialize to empty

        if $subtitles && [ -n "$subtitle_file" ]; then
          temp_subtitle_file=$(prepare_subtitles "$start_time" "$end_time" "$subtitle_file")
          if [ -n "$temp_subtitle_file" ]; then
              current_subtitle_arg="$temp_subtitle_file"
              current_python_script="llm-python-vision-multi-images-file.py"
          else
              current_subtitle_arg=""
              current_python_script="llm-python-vision-multi-images.py"
          fi
        fi

        # Construct the command arguments
        cmd_args=("$prompt" "$temperature") # Prompt is sys.argv[1], Temperature is sys.argv[2]
        if [ -n "$current_subtitle_arg" ]; then
          cmd_args+=("$current_subtitle_arg") # Subtitle is sys.argv[3] for file script
        fi
        cmd_args+=("${subset[@]}") # Images start at sys.argv[3] for non-file script, sys.argv[4] for file script

        echo "Sending frames ${start_frame}-${end_frame} to LLM..." >&2 # Debugging output

        # Call the appropriate python script and time it
        output=$(time -p $current_python_script "${cmd_args[@]}")

        # Append the frame numbers and the output to the output file
        echo "Frames ${start_frame}-${end_frame} (time ${start_time}s-${end_time}s):" >> "$output_file"
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
  preprompt="You are reviewing the visual content of a video."
  if [ -n "$title" ]; then
    preprompt+=" The video is titled \"${title}\"."
  fi
  preprompt+=" Below you will find a series of frame-by-frame descriptions."
  postprompt="Based on the frame-by-frame descriptions (and any subtitles, if provided), write a single, coherent summary of the video. - Keep it under 250 words. - Use present-tense, third-person narrative. - Highlight main events, key characters, and important dialogue from subtitles. - End with a one-sentence conclusion that captures the overall outcome."

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
    cmd_args=("$prompt" "$temperature") # Prompt is sys.argv[1], Temperature is sys.argv[2]
    if [ -n "$current_subtitle_arg" ]; then
      cmd_args+=("$current_subtitle_arg") # Subtitle is sys.argv[3] for file script
    fi
    cmd_args+=("${images[@]}") # Images start at sys.argv[3] for non-file script, sys.argv[4] for file script

    echo "Sending frames 1-${num_images} to LLM..." >&2 # Debugging output

    # Call the appropriate python script and time it
    output=$(time -p $current_python_script "${cmd_args[@]}")

    # Append the frame numbers and the output to the output file
    echo "Frames 1-${num_images} (time ${start_time}s-${end_time}s):" >> "$output_file"
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

      if $subtitles && [ -n "$subtitle_file" ]; then
        temp_subtitle_file=$(prepare_subtitles "$start_time" "$end_time" "$subtitle_file")
        if [ -n "$temp_subtitle_file" ]; then
            current_subtitle_arg="$temp_subtitle_file"
            current_python_script="llm-python-vision-multi-images-file.py"
        else
            current_subtitle_arg=""
            current_python_script="llm-python-vision-multi-images.py"
        fi
      fi

      # Construct the command arguments
      cmd_args=("$prompt" "$temperature") # Prompt is sys.argv[1], Temperature is sys.argv[2]
      if [ -n "$current_subtitle_arg" ]; then
        cmd_args+=("$current_subtitle_arg") # Subtitle is sys.argv[3] for file script
      fi
      cmd_args+=("${subset[@]}") # Images start at sys.argv[3] for non-file script, sys.argv[4] for file script

      echo "Sending frames ${start_frame}-${end_frame} to LLM..." >&2 # Debugging output

      # Call the appropriate python script and time it
      output=$(time -p $current_python_script "${cmd_args[@]}")

      # Append the frame numbers and the output to the output file
      echo "Frames ${start_frame}-${end_frame} (time ${start_time}s-${end_time}s):" >> "$output_file"
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
