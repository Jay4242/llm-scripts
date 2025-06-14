#!/bin/bash

# Clear any existing files in /dev/shm/llm-ffmpeg-edit/
if [ -d /dev/shm/llm-ffmpeg-edit/ ]; then
  rm -rf /dev/shm/llm-ffmpeg-edit/*
fi

mkdir -p /dev/shm/llm-ffmpeg-edit/ || exit 1
temp_dir=/dev/shm/llm-ffmpeg-edit/

# Default values for options
scene_change=false
scene_threshold=0.3 # Threshold for scene change detection
use_cookies=false
frame_rate=2         # Frames per second to extract
frames_per_batch=20  # Number of frames to send to LLM per batch
output_clip_name="clipped_video.mp4" # Default output filename for the clipped video
full_mode=false      # New: Option to scan full video and concatenate all detections

# Variables for tracking the *first* continuous segment (for non-full mode)
first_clip_start_time=-1
first_clip_end_time=-1
first_clip_identified=false # Flag to indicate if the first clip has been fully identified (start and end)

# Variables for tracking the *current* continuous segment (for building `all_detected_segments` and also used by first_clip logic)
current_segment_start=-1
current_segment_end=-1
segment_in_progress=false # Flag to indicate if a continuous segment is currently being built

# Array to store all detected segments [start_time,end_time] for --full mode
declare -a all_detected_segments

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -s|--scene-change)
      scene_change=true
      shift
      ;;
    -c|--cookies)
      use_cookies=true
      shift
      ;;
    -o|--output-file)
      output_clip_name="$2"
      shift 2
      ;;
    -fr|--frame-rate)
      frame_rate="$2"
      shift 2
      ;;
    -fb|--frames-per-batch)
      frames_per_batch="$2"
      shift 2
      ;;
    -f|--full) # New flag for full mode
      full_mode=true
      shift
      ;;
    *)
      # Positional arguments: video_url and thing_to_detect
      if [ -z "$video_url" ]; then
        video_url="$1"
      elif [ -z "$thing_to_detect" ]; then
        thing_to_detect="$1"
      else
        echo "Error: Unknown argument or too many positional arguments: $1" >&2
        exit 1
      fi
      shift
      ;;
  esac
done

# Check if mandatory arguments are provided
if [ -z "$video_url" ] || [ -z "$thing_to_detect" ]; then
  echo "Usage: $0 [-s|--scene-change] [-c|--cookies] [-o|--output-file <filename>] [-fr|--frame-rate <rate>] [-fb|--frames-per-batch <num>] [-f|--full] <video_url> <thing_to_detect>" >&2
  echo "Example: $0 https://www.youtube.com/watch?v=dQw4w9WgXcQ 'Rick Astley singing'" >&2
  exit 1
fi

# Construct the cookies option for yt-dlp
cookies_option=""
if $use_cookies; then
  cookies_option="--cookies-from-browser chrome"
fi

echo "Downloading video..." >&2
# Download the video
yt-dlp --no-warnings ${cookies_option} -q -f "bestvideo[height<=720]+bestaudio/best[height<=720]" -o "${temp_dir}/video.%(ext)s" "${video_url}" || {
  echo "Error: Failed to download video from ${video_url}. Exiting." >&2
  exit 1
}
video="${temp_dir}/video.$(echo $(ls ${temp_dir}/video.* | cut -d '.' -f 2) )"

echo "Extracting frames..." >&2
# Extract frames from the video
if $scene_change; then
  # Extract scene frames with fixed frame rate and scene detection
  ffmpeg -i "${video}" -vf "fps=${frame_rate},select='gt(scene,${scene_threshold})'" -vsync vfr "${temp_dir}/frame_%04d.jpg" 2>/dev/null
else
  # Extract frames at a fixed rate
  ffmpeg -i "${video}" -vf "fps=${frame_rate}" "${temp_dir}/frame_%04d.jpg" 2>/dev/null
fi

# Check if any frames were extracted
images=(${temp_dir}/frame_*.jpg)
num_images=${#images[@]}
if [ "$num_images" -eq 0 ]; then
  echo "Error: No frames extracted from the video. Exiting." >&2
  exit 1
fi

echo "Analyzing video for '${thing_to_detect}'..." >&2

# Loop through the images in batches for detection
for ((i=0; i<num_images; i+=$frames_per_batch)); do
  subset=("${images[@]:i:$frames_per_batch}")
  num_subset=${#subset[@]}

  # Get the starting and ending frame numbers for the current batch
  start_frame=$((i + 1))
  end_frame=$((i + $num_subset))

  # Calculate the start and end times in seconds for the current batch (using bc for float arithmetic)
  current_batch_start_time=$(echo "scale=3; ($start_frame - 1) / $frame_rate" | bc -l)
  current_batch_end_time=$(echo "scale=3; $end_frame / $frame_rate" | bc -l)

  # Construct the LLM prompt for detection. It's crucial to ask for a simple YES/NO.
  detection_prompt="Is '${thing_to_detect}' visible in any of these frames? Answer only 'YES' or 'NO'. Do not add any other text."

  # Construct the command arguments for the Python script
  cmd_args=("$detection_prompt")
  cmd_args+=("${subset[@]}")

  echo "  Checking frames ${start_frame}-${end_frame} (${current_batch_start_time}s-${current_batch_end_time}s)..." >&2

  # Call the llm-python-vision-multi-images.py script
  llm_output=$(llm-python-vision-multi-images.py "${cmd_args[@]}")
  llm_exit_code=$?

  echo "    LLM Raw Output: '$llm_output'" >&2 # Added line to print LLM output

  if [ $llm_exit_code -ne 0 ]; then
    echo "  Warning: LLM script exited with error code $llm_exit_code for frames ${start_frame}-${end_frame}. Output: $llm_output. Skipping this batch." >&2
    continue
  fi

  # Trim whitespace and newlines from LLM output for reliable comparison
  llm_output_trimmed=$(echo "$llm_output" | tr -d '\n\r' | xargs | tr '[:lower:]' '[:upper:]') # Convert to uppercase for case-insensitive check

  if [[ "$llm_output_trimmed" == "YES" ]]; then
    if ! $segment_in_progress; then
      # Start of a new continuous segment
      current_segment_start=$current_batch_start_time
      segment_in_progress=true
      echo "  Detected '${thing_to_detect}' starting at ${current_segment_start}s (frame ${start_frame})." >&2
    fi
    current_segment_end=$current_batch_end_time # Extend the end time of the current segment
  else # LLM output is NO
    if $segment_in_progress; then
      # A continuous segment just ended
      detected_end_frame_num=$(echo "scale=0; ($current_segment_end * $frame_rate) + 1" | bc) # Calculate frame number for the end of the detected segment
      all_detected_segments+=("${current_segment_start},${current_segment_end}")
      echo "  Detection of '${thing_to_detect}' ended at ${current_segment_end}s (frame ${detected_end_frame_num}). Stored segment: ${current_segment_start}-${current_segment_end}" >&2
      
      # If not in full mode, and this is the first segment we've identified, then we are done.
      if ! $full_mode && ! $first_clip_identified; then
        first_clip_start_time=$current_segment_start
        first_clip_end_time=$current_segment_end
        first_clip_identified=true
        break # Exit the loop as we found the first continuous segment
      fi

      segment_in_progress=false
      current_segment_start=-1 # Reset
      current_segment_end=-1   # Reset
    fi
  fi
done # End of loop through batches

# After the loop, handle any segment that was in progress at the end of the video
if $segment_in_progress; then
  detected_end_frame_num=$(echo "scale=0; ($current_segment_end * $frame_rate) + 1" | bc) # Calculate frame number for the end of the detected segment
  all_detected_segments+=("${current_segment_start},${current_segment_end}")
  echo "  Detection of '${thing_to_detect}' ended at ${current_segment_end}s (end of video). Stored segment: ${current_segment_start}-${current_segment_end}" >&2
  # If not in full mode, and this is the first segment we've identified (because it went to end of video)
  if ! $full_mode && ! $first_clip_identified; then
    first_clip_start_time=$current_segment_start
    first_clip_end_time=$current_segment_end
    first_clip_identified=true
  fi
fi

# --- Clipping Logic ---
if $full_mode; then
  if [ ${#all_detected_segments[@]} -eq 0 ]; then
    echo "Could not detect '${thing_to_detect}' in the video. No clip was created." >&2
  else
    echo "Concatenating all detected segments..." >&2
    temp_clips_dir="${temp_dir}/clips"
    mkdir -p "${temp_clips_dir}" || { echo "Error: Failed to create temporary clips directory." >&2; exit 1; }
    concat_list_file="${temp_dir}/concat_list.txt"
    > "$concat_list_file" # Clear previous content

    segment_counter=0
    for segment_pair in "${all_detected_segments[@]}"; do
      IFS=',' read -r start_time end_time <<< "$segment_pair"
      duration=$(echo "scale=3; $end_time - $start_time" | bc -l)

      if (( $(echo "$duration <= 0" | bc -l) )); then
        echo "Warning: Skipping zero or negative duration segment: ${start_time}-${end_time}" >&2
        continue
      fi

      segment_counter=$((segment_counter + 1))
      output_segment_path="${temp_clips_dir}/segment_$(printf "%04d" $segment_counter).mp4"

      echo "  Extracting segment ${segment_counter}: ${start_time}s to ${end_time}s (duration: ${duration}s)" >&2
      ffmpeg -ss "${start_time}" -i "${video}" -t "${duration}" -c copy "${output_segment_path}" 2>/dev/null || {
        echo "Warning: Failed to extract segment ${segment_counter} with stream copy. Attempting re-encode." >&2
        ffmpeg -ss "${start_time}" -i "${video}" -t "${duration}" "${output_segment_path}" 2>/dev/null || {
          echo "Error: Failed to extract segment ${segment_counter} even with re-encoding. Skipping this segment." >&2
          continue # Skip to next segment
        }
      }
      echo "file '${output_segment_path}'" >> "$concat_list_file"
    done

    if [ ! -s "$concat_list_file" ]; then
      echo "Error: No valid segments were extracted for concatenation. No clip was created." >&2
      rm -rf "${temp_clips_dir}"
      rm -f "$concat_list_file"
      exit 1
    fi

    echo "Final concatenation of segments into ${output_clip_name}..." >&2
    final_output_clip_path="${temp_dir}/${output_clip_name}"
    ffmpeg -f concat -safe 0 -i "$concat_list_file" -c copy "${final_output_clip_path}" 2>/dev/null || {
      echo "Error: Failed to concatenate segments. Exiting." >&2
      rm -rf "${temp_clips_dir}"
      rm -f "$concat_list_file"
      exit 1
    }

    if [ -f "${final_output_clip_path}" ]; then
      echo "Clipped video saved to: ${final_output_clip_path}"
      cp "${final_output_clip_path}" . || {
        echo "Warning: Failed to copy clipped video to current directory. It remains at ${final_output_clip_path}" >&2
      }
      echo "Clipped video copied to current directory: ./${output_clip_name}"
    else
      echo "Error: Final clipped video file not found at ${final_output_clip_path} after ffmpeg command." >&2
    fi
    rm -rf "${temp_clips_dir}" # Clean up individual segment clips
    rm -f "$concat_list_file"
  fi
else # Original non-full mode clipping logic
  # Use first_clip_start_time and first_clip_end_time
  if (( $(echo "$first_clip_start_time >= 0" | bc -l) )); then
    # Ensure first_clip_end_time is valid and greater than first_clip_start_time
    if (( $(echo "$first_clip_end_time <= $first_clip_start_time" | bc -l) )); then
      echo "Warning: Detected segment is too short or invalid (${first_clip_start_time}s to ${first_clip_end_time}s). Adjusting first_clip_end_time to ensure minimum 1-second duration." >&2
      first_clip_end_time=$(echo "scale=3; $first_clip_start_time + 1" | bc -l)
    fi

    clip_duration=$(echo "scale=3; $first_clip_end_time - $first_clip_start_time" | bc -l)

    echo "Clipping video from ${first_clip_start_time}s to ${first_clip_end_time}s (duration: ${clip_duration}s)..." >&2
    output_clip_path="${temp_dir}/${output_clip_name}"

    ffmpeg -ss "${first_clip_start_time}" -i "${video}" -t "${clip_duration}" -c copy "${output_clip_path}" 2>/dev/null || {
      echo "Warning: Failed to clip video with stream copy. This can happen if cut points are not on keyframes." >&2
      echo "Attempting re-encode (this may be slower and re-compress the video)." >&2
      ffmpeg -ss "${first_clip_start_time}" -i "${video}" -t "${clip_duration}" "${output_clip_path}" 2>/dev/null || {
        echo "Error: Failed to clip video even with re-encoding. Exiting." >&2
        exit 1
      }
    }

    if [ -f "${output_clip_path}" ]; then
      echo "Clipped video saved to: ${output_clip_path}"
      cp "${output_clip_path}" . || {
        echo "Warning: Failed to copy clipped video to current directory. It remains at ${output_clip_path}" >&2
      }
      echo "Clipped video copied to current directory: ./${output_clip_name}"
    else
      echo "Error: Clipped video file not found at ${output_clip_path} after ffmpeg command." >&2
    fi
  else
    echo "Could not detect '${thing_to_detect}' in the video. No clip was created." >&2
  fi
fi

# Clean up temporary files (optional, uncomment to enable)
# rm -rf "${temp_dir}"
