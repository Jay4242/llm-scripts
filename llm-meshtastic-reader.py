import meshtastic
import meshtastic.serial_interface
from pubsub import pub
import logging
import sys
import time
from openai import OpenAI
import httpx

# LLM Configuration - adjust these as needed
LLM_BASE_URL = "http://localhost:9090/v1"
LLM_API_KEY = "none"
LLM_MODEL = "gemma-3-4b-it-q8_0"
LLM_SYSTEM_PROMPT = "You are a helpful assistant responding to Meshtastic text messages."
LLM_PREPROMPT = "The user says: "
LLM_POSTPROMPT = "Respond to the user."
LLM_TEMPERATURE = 0.7
LLM_TIMEOUT = 3600

MAX_MESSAGE_LENGTH = 200  # Maximum characters per message

def onReceive(packet, interface):
    """
    This function is called when a message is received.
    It checks if the message is for this node, sends the message to the LLM,
    and sends the LLM's response back to the sender.
    """
    try:
        if packet["to"] == interface.myInfo.my_node_num:
            print(f"Received message for this node: {packet}")
            
            # Extract the message payload
            received_text = packet["decoded"].get("text")
            if not received_text:
                print("No text found in decoded payload.")
                return

            # Construct the messages for the LLM
            messages = [
                {"role": "system", "content": LLM_SYSTEM_PROMPT},
                {"role": "user", "content": LLM_PREPROMPT},
                {"role": "user", "content": received_text},
                {"role": "user", "content": LLM_POSTPROMPT}
            ]

            # Send the message to the LLM and get the response
            try:
                client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY, timeout=httpx.Timeout(LLM_TIMEOUT))
                completion = client.chat.completions.create(
                    model=LLM_MODEL,
                    messages=messages,
                    temperature=LLM_TEMPERATURE,
                )
                response_text = completion.choices[0].message.content.strip()
            except Exception as e:
                logging.error(f"Error during LLM processing: {e}")
                response_text = f"Error processing message: {e}"

            # Split the LLM's response into multiple messages if it's too long
            while len(response_text) > 0:
                chunk = response_text[:MAX_MESSAGE_LENGTH]
                response_text = response_text[MAX_MESSAGE_LENGTH:]

                # Send the chunk back to the sender
                print(f"Sending response chunk: {chunk}")  # Debug print
                interface.sendText(chunk, destinationId=packet["from"])
                print(f"Sent response chunk: {chunk}")

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
while True:
    time.sleep(1)
