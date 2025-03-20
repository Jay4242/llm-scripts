#!/usr/bin/env python3
##Broken Order :/

import sys
import json
import traceback
import base64
import os
import uuid
import socket
import ssl
import hashlib
import websocket
import time
import re
import io

try:
    from websocket import enableTrace
except ImportError:
    print("Error: The 'websocket-client' package is not installed or is not correctly configured.")
    print("Please ensure that the package is installed. You can install it using: pip install websocket-client")
    sys.exit(1)

try:
    from PIL import Image, ImageTk
    import tkinter as tk
except ImportError:
    print("Error: The 'Pillow' and 'tkinter' packages are not installed.")
    print("Also ensure tkinter is installed. On Debian/Ubuntu: sudo apt-get install python3-tk")
    sys.exit(1)


MAX_RETRIES = 3
SOCKET_TIMEOUT = 30  # Increased timeout to 30 seconds
RETRY_DELAY = 1 # Wait 1 second before retrying

def generate_sec_websocket_key():
    """Generate a random Sec-WebSocket-Key."""
    # Use a more robust method for generating a random key
    random_bytes = os.urandom(16)
    sec_key = base64.b64encode(random_bytes).decode('utf-8')
    return sec_key

def display_image(image_data):
    """Displays a base64 encoded image in a Tkinter window."""
    try:
        # Decode the base64 image data
        image_bytes = base64.b64decode(image_data)
        # Open the image using PIL
        image = Image.open(io.BytesIO(image_bytes))
        # Create a Tkinter window
        root = tk.Tk()
        root.title("Wolfram Alpha Image")
        # Convert the PIL image to a Tkinter-compatible image
        photo = ImageTk.PhotoImage(image)
        # Create a label to display the image
        label = tk.Label(root, image=photo)
        label.image = photo  # Keep a reference to the image
        label.pack()
        # Start the Tkinter event loop
        root.mainloop()
    except Exception as e:
        print(f"Error displaying image: {e}")
        traceback.print_exc()

def get_wolfram_alpha_answer(search_term):
    """
    Fetches the Wolfram Alpha search page for a given term, parses the result,
    and returns the answer.
    """
    url = "wss://gateway.wolframalpha.com/gateway"
    origin = "https://www.wolframalpha.com"

    headers = {
        "Origin": origin,
    }

    for attempt in range(MAX_RETRIES):
        try:
            ready_received = False # Define ready_received here
            ws = websocket.create_connection(url,
                                             timeout=SOCKET_TIMEOUT,
                                             header= [f"{k}: {v}" for k, v in headers.items()])


            def send_message(message):
                """Sends a JSON message to the WebSocket."""
                ws.send(json.dumps(message))

            # Send init message
            send_message({"type": "ready", "category": "websocket"})

            # Send newQuery message with more parameters
            new_query_message = {
                "type": "newQuery",
                "locationId": "/input?i=" + search_term + "_en_light",
                "language": "en",
                "displayDebuggingInfo": False,
                "yellowIsError": False,
                "requestSidebarAd": True,
                "category": "results",
                "input": search_term,
                "i2d": False,
                "assumption": [],
                "apiParams": {},
                "file": None,
                "theme": "light"
            }
            send_message(new_query_message)

            all_plaintext = {} # Dictionary to store all plaintext results with step number
            query_completed = False # Flag to indicate if queryComplete message was received
            all_plaintext[0] = search_term # Initialize the first step with the search term

            while True:
                start_time = time.time()
                try:
                    message =  ws.recv()
                    end_time = time.time()
                    #print(f"Received message in {end_time - start_time:.2f} seconds: {message}") # ADDED DEBUGGING OUTPUT

                except websocket._exceptions.WebSocketTimeoutException as e:
                    end_time = time.time()
                    #print(f"WebSocketTimeoutException after {end_time - start_time:.2f} seconds: {e}") # Removed debugging output
                    ws.close()
                    break
                except Exception as e:
                    #print(f"Error receiving message: {e}") # Removed debugging output
                    traceback.print_exc()
                    ws.close()
                    break

                try:
                    result_json = json.loads(message)
                    if result_json.get("type") == "ready" and result_json.get("category") == "websocket":
                        if not ready_received:
                            #print("Received ready message, sending acknowledgement.") # Removed debugging output
                            send_message({"type": "ack", "message": "ready"})
                            ready_received = True
                    elif result_json.get("type") == "pods":
                        pods = result_json.get("pods")
                        if pods:
                            for pod in pods:
                                if pod.get('title') == "Solutions":
                                    subpods = pod.get("subpods")
                                    if subpods:
                                        for subpod in subpods:
                                            plaintext = subpod.get("plaintext")
                                            if plaintext:
                                                plaintext = plaintext.replace("|", "") # Remove purely visual pipes
                                                all_plaintext[2] = plaintext # Add to step 2, the solution
                                            minput = subpod.get("minput")
                                            if minput:
                                                pass
                                            moutput = subpod.get("moutput")
                                            if moutput:
                                                pass
                                elif pod.get('title') == "Input" or pod.get('title') == "Alternate form":
                                    subpods = pod.get("subpods")
                                    if subpods:
                                        for subpod in subpods:
                                            plaintext = subpod.get("plaintext")
                                            if plaintext and plaintext != search_term:
                                                plaintext = plaintext.replace("|", "") # Remove purely visual pipes
                                                all_plaintext[1] = plaintext # Add to step 1
                    elif result_json.get("type") == "stepByStep":
                        pod = result_json.get("pod")
                        if pod:
                            subpods = pod.get("subpods")
                            if subpods:
                                for subpod in subpods:
                                    plaintext = subpod.get("plaintext")
                                    if plaintext:
                                        plaintext = plaintext.replace("|", "") # Remove purely visual pipes
                                        step_number = result_json.get("stepNumber")
                                        all_plaintext[step_number + 3] = plaintext # Store with step number
                    elif result_json.get("type") == "queryComplete":
                        #print("Query complete message received.") # Removed debugging output
                        query_completed = True
                        ws.close()
                        break
                    elif result_json.get("type") == "error":
                        #print(f"Error message received: {result_json}") # Removed debugging output
                        ws.close()
                        break
                    elif result_json.get("type") == "info":
                        #print(f"Info message received: {result_json}") # Removed debugging output
                        pass
                except json.JSONDecodeError as e:
                    #print(f"JSONDecodeError: {e}.  Message was: {message}") # Removed debugging output
                    ws.close()
                    break
                except Exception as e:
                    #print(f"Error processing message: {e}") # Removed debugging output
                    traceback.print_exc()
                    ws.close()
                    break

            if query_completed:
                break # Exit the retry loop if query is completed

        except socket.timeout as e:
            #print(f"Attempt {attempt + 1} failed: Socket timeout - {e}") # Removed debugging output
            if attempt == MAX_RETRIES - 1:
                #print("Max retries reached.  Failed to connect to the websocket.") # Removed debugging output
                break
            time.sleep(RETRY_DELAY) # Wait before retrying
        except Exception as e:
            #print(f"Attempt {attempt + 1} failed: {e}") # Removed debugging output
            traceback.print_exc()
            if attempt == MAX_RETRIES - 1:
                #print("Max retries reached.  Failed to connect to the websocket.") # Removed debugging output
                break

    ws.close()
    # Sort the steps by step number
    sorted_steps = [all_plaintext[key] for key in sorted(all_plaintext.keys())]
    return sorted_steps

if __name__ == '__main__':
    if len(sys.argv) > 1:
        search_term = sys.argv[1]
    else:
        search_term = "x^2 = 64"
        print("No search term provided. Using default search term: 'x^2 = 64'")

    steps = get_wolfram_alpha_answer(search_term)

    if steps:
        print("\nSolution steps:")
        for i, step in enumerate(steps):
            print(f"{i+1}: {step}")
    else:
        print("Could not retrieve the solution steps from Wolfram Alpha.")
