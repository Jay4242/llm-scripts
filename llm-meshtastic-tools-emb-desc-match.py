import meshtastic
import meshtastic.serial_interface
from pubsub import pub
import logging
import sys
import time
from openai import OpenAI
import httpx
from datetime import datetime
import subprocess
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import json
import random

# LLM Configuration - adjust these as needed
LLM_BASE_URL = "http://localhost:9090/v1"  # Base URL for regular LLM
EMBEDDING_BASE_URL = "http://localhost:9494/v1" # Base URL for embedding LLM
LLM_API_KEY = "none"
LLM_MODEL = "gemma-3-4b-it-q8_0"  # Using embedding model
LLM_SYSTEM_PROMPT = """You are a helpful assistant responding to Meshtastic text messages."""
LLM_PREPROMPT = "The user says: "
LLM_POSTPROMPT = "Respond to the user."
LLM_TEMPERATURE = 0.7
LLM_TIMEOUT = 3600

MAX_MESSAGE_LENGTH = 200  # Maximum characters per message

# Define the tools and their descriptions
TOOLS = {
    "system_info": {
        "description": "System information, such as CPU usage, memory usage, and uptime.",
        "function": lambda input: subprocess.check_output(["uptime"]).decode("utf-8")
    },
    "weather_report": {
        "description": "Weather Report",
        "function": lambda input: subprocess.check_output(["llm-mesh-weather.bash"]).decode("utf-8")
    },
    "chat": {
        "description": "General chat.  Good for jokes.  Advice.  Etc. 👍",
        "function": lambda input: get_llm_response(input)
    },
    "numbers_station": {
        "description": "Random numbers, like a numbers station.",
        "function": lambda input: ''.join(random.choice('0123456789') for _ in range(200))
    }
}

def get_embedding(text):
    """
    Generates an embedding for the given text using the OpenAI API.
    """
    client = OpenAI(base_url=EMBEDDING_BASE_URL, api_key=LLM_API_KEY, timeout=httpx.Timeout(LLM_TIMEOUT))
    try:
        response = client.embeddings.create(
            model="nomic-embed-text-v1.5.q8_0",
            input=[text]
        )
        return np.array(response.data[0].embedding)
    except Exception as e:
        logging.error(f"Error generating embedding: {e}")
        return None

def get_llm_response(user_message):
    """
    Sends the user message to the LLM and returns the response.
    """
    try:
        client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY, timeout=httpx.Timeout(LLM_TIMEOUT))
        
        # Get the current date and time
        now = datetime.now()
        current_time = now.strftime("%Y-%m-%d %A %H:%M:%S")

        # Construct the messages for the LLM, including the current time in the system prompt
        system_prompt = f"{LLM_SYSTEM_PROMPT} The current date and time is: {current_time}."
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": LLM_PREPROMPT},
            {"role": "user", "content": user_message},
            {"role": "user", "content": LLM_POSTPROMPT}
        ]
        
        completion = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=LLM_TEMPERATURE,
        )
        response_text = completion.choices[0].message.content.strip()
        return response_text
    except Exception as e:
        logging.error(f"Error during LLM processing: {e}")
        return f"Error processing message: {e}"

def select_tool(user_message, tools):
    """
    Selects the most relevant tool based on the user message using embeddings.
    """
    user_embedding = get_embedding(user_message)
    if user_embedding is None:
        return None, "Error: Could not generate embedding for user message."

    best_tool = None
    best_similarity = -1
    
    for tool_name, tool_data in tools.items():
        tool_embedding = get_embedding(tool_data["description"])
        if tool_embedding is None:
            logging.warning(f"Could not generate embedding for tool: {tool_name}")
            continue
            
        similarity = cosine_similarity(user_embedding.reshape(1, -1), tool_embedding.reshape(1, -1))[0][0]
        
        if similarity > best_similarity:
            best_similarity = similarity
            best_tool = tool_name
            
    if best_tool:
        return best_tool, None
    else:
        return None, "Error: No suitable tool found."


def onReceive(packet, interface):
    """
    This function is called when a message is received.
    It checks if the message is for this node, selects a tool,
    and sends the tool's response back to the sender.
    """
    try:
        if packet["to"] == interface.myInfo.my_node_num:
            print(f"Received message for this node: {packet}")
            
            # Extract the message payload
            received_text = packet["decoded"].get("text")
            if not received_text:
                print("No text found in decoded payload.")
                return

            # Select a tool based on the received text
            tool_name, error_message = select_tool(received_text, TOOLS)
            print(f"Selected tool: {tool_name}")  # Debug print
            if error_message:
                response_text = error_message
            else:
                try:
                    # Execute the selected tool
                    tool_output = TOOLS[tool_name]["function"](received_text)
                    response_text = tool_output
                except Exception as e:
                    logging.error(f"Error executing tool: {e}")
                    response_text = f"Error executing tool: {e}"

            # Split the LLM's response into multiple messages if it's too long
            while len(response_text) > 0:
                chunk = response_text[:MAX_MESSAGE_LENGTH]
                response_text = response_text[MAX_MESSAGE_LENGTH:]

                # Send the chunk back to the sender
                print(f"Sending response chunk: {chunk}")  # Debug print
                interface.sendText(chunk, destinationId=packet["from"])
                print(f"Sent response chunk: {chunk}")
                time.sleep(1)  # Add a 1-second delay between chunks

    except Exception as e:
        logging.error(f"Error in onReceive: {e}")


def onConnection(interface, topic=pub.AUTO_TOPIC):
    """This is called when we (re)connect to the radio."""
    print(f"Connected to radio {interface.myInfo}")


pub.subscribe(onReceive, "meshtastic.receive")
pub.subscribe(onConnection, "meshtastic.connection.established")

# By default will try to find a meshtastic device, otherwise provide a device path like /dev/ttyUSB0
try:
    interface = meshtastic.serial_interface.SerialInterface()
except Exception as e:
    print(f"Error connecting to device: {e}")
    sys.exit(1)

# Keep the script running to receive messages
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Ctrl+C detected. Closing connection...")
    interface.close()
    print("Connection closed. Exiting.")
    sys.exit(0)
