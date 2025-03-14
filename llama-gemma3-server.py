import flask
from flask import Flask, request, jsonify
import os
import tempfile
import subprocess
import threading
import shutil
import base64

app = Flask(__name__)

TEMP_DIR_PREFIX = "/dev/shm/llama-gemma3-server_"
command_lock = threading.Lock()
MODEL_DIR = ""  ## Your model directory here.
MODEL_FILE = "google_gemma-3-4b-it-Q8_0.gguf"
MMPROJ_FILE = "mmproj-google_gemma-3-4b-it-f32.gguf"
IMAGE_DIR_NAME = "images"  # Subdirectory for images

# Global variable to track if initialization has been done
initialization_done = False

@app.route('/')
def hello_world():
    return 'Hello, World!'

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    global initialization_done
    if not initialization_done:
        create_temp_dir()
        initialization_done = True

    data = request.get_json()
    print(f"Received data: {data}")  # Debugging

    # Extract parameters from the request
    contents = data.get('messages')[1]['content']

    port = get_port()
    temp_dir = TEMP_DIR_PREFIX + str(port)
    image_dir = os.path.join(temp_dir, IMAGE_DIR_NAME)  # Path to the images subdirectory
    model = os.path.join(temp_dir, MODEL_FILE)
    mmproj = os.path.join(temp_dir, MMPROJ_FILE)

    prompts = []
    image_paths = []

    # Iterate through the content array
    for item in contents:
        if item['type'] == 'text':
            prompts.append(item['text'])
        elif item['type'] == 'image_url':
            image_data = item['image_url']['url'].split(',')[1]
            image_path = None
            try:
                # Check if image_data is a string
                if not isinstance(image_data, str):
                    raise ValueError("image_data must be a string")

                # Decode base64 image data
                image_bytes = base64.b64decode(image_data)

                # Create a temporary file in the images subdirectory
                temp_image_file = tempfile.NamedTemporaryFile(dir=image_dir, delete=False, suffix=".jpg")  # You might want to adjust the suffix based on the image type
                image_path = temp_image_file.name

                # Write the image bytes to the temporary file
                temp_image_file.write(image_bytes)
                temp_image_file.close()

                print(f"Saved image to temporary file: {image_path}")  # Debugging
                image_paths.append(image_path)
            except Exception as e:
                print(f"Error processing image data: {e}")
                return jsonify({"error": f"Error processing image data: {e}"}), 400

    # Construct the command
    command = ["/usr/local/bin/llama-gemma3-cli"]  # Assuming llama-gemma3-cli is in /usr/local/bin
    command.extend(["-m", model])
    command.extend(["--mmproj", mmproj])
    
    # Combine all prompts into a single prompt
    combined_prompt = " ".join(prompts)
    if combined_prompt:
        command.extend(["-p", f'"{combined_prompt}"'])
    
    # Add all image paths to the command
    for image_path in image_paths:
        command.extend(["--image", image_path])
    
    command.extend(["--log-disable"])

    print(f"Executing command: {' '.join(command)}")  # Debugging

    # Execute the command
    with command_lock:
        print("Acquired command lock")  # Debugging
        try:
            print("About to run subprocess")  # Debugging
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            print("Subprocess finished running")  # Debugging
            output = result.stdout
            print(f"Command output: {output}")  # Debugging

            # Filter the output
            lines = output.splitlines()
            filtered_lines = []
            start_found = False
            for line in lines:
                if start_found:
                    filtered_lines.append(line)
                if line.startswith("main: /dev/shm/llama-gemma3-server_5000/google_gemma-3-4b-it-Q8_0.gguf"):
                    start_found = True
            filtered_output = "\n".join(filtered_lines)

            return jsonify({"choices": [{"message": {"content": filtered_output}}]})
        except subprocess.CalledProcessError as e:
            print(f"Command failed with error: {e}")  # Debugging
            return jsonify({"error": str(e)}), 500
        finally:
            print("Releasing command lock")  # Debugging
            # Clean up the temporary image files
            for image_path in image_paths:
                try:
                    os.remove(image_path)
                    print(f"Deleted temporary image file: {image_path}")  # Debugging
                except OSError as e:
                    print(f"Error deleting temporary image file: {e}")


def create_temp_dir():
    port = get_port()
    temp_dir = TEMP_DIR_PREFIX + str(port)
    image_dir = os.path.join(temp_dir, IMAGE_DIR_NAME)  # Path to the images subdirectory
    try:
        os.makedirs(temp_dir, exist_ok=True)
        os.makedirs(image_dir, exist_ok=True)  # Create the images subdirectory
        print(f"Created temporary directory: {temp_dir}")
        print(f"Created images subdirectory: {image_dir}")

        # Copy model files to the temp directory if they don't exist
        model_src = os.path.join(MODEL_DIR, MODEL_FILE)
        mmproj_src = os.path.join(MODEL_DIR, MMPROJ_FILE)
        model_dst = os.path.join(temp_dir, MODEL_FILE)
        mmproj_dst = os.path.join(temp_dir, MMPROJ_FILE)

        if not os.path.exists(model_dst):
            shutil.copy(model_src, model_dst)
            print(f"Copied model file to {temp_dir}")
        else:
            print(f"Model file already exists in {temp_dir}")

        if not os.path.exists(mmproj_dst):
            shutil.copy(mmproj_src, mmproj_dst)
            print(f"Copied mmproj file to {temp_dir}")
        else:
            print(f"Mmproj file already exists in {temp_dir}")

    except OSError as e:
        print(f"Error creating temporary directory: {e}")
    except FileNotFoundError as e:
        print(f"Error copying model files: {e}")


def get_port():
    # This is a placeholder.  In a real application, you would
    # likely get the port number from a configuration file or
    # environment variable.  For now, we'll just hardcode it.
    #
    # Note that if you change the port, you'll need to delete the
    # temp directory manually, as it's named based on the port.
    return 5000

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=get_port())
