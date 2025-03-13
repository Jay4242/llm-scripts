#!/usr/bin/env python3

import sys
import time
import json
import os
import signal
import threading
import requests
from dotenv import load_dotenv
import pyttsx3
import subprocess
import re
import argparse
from datetime import datetime
import logging
import socket

load_dotenv()

# Configuration
ZIP_CODE = os.getenv("ZIP_CODE")
TEMPERATURE = 0.8
MODEL = "gemma-3-4b-it-q8_0"
BASE_URL = os.getenv("BASE_URL")
API_KEY = "None"
ESPEAK_SPEED = 160
YT_DLP_FORMAT = "bestaudio/best"
MAX_LAST_PLAYED = 10  # Maximum number of songs to keep in last_played list
MAX_RUNS = 1000 # Maximum runs before exiting.  Remove for infinite loop.
MPV_SOCKET = "/dev/shm/mpv_socket"

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize pyttsx3
engine = pyttsx3.init()
engine.setProperty('rate', ESPEAK_SPEED)

last_played = []
exiting = False  # Global flag to prevent re-entering the signal handler
mpv_process = None # Global variable to store the mpv process

def get_location_from_zip(zip_code):
    """Fetches latitude and longitude from a zip code using Nominatim."""
    assert isinstance(zip_code, str), "Zip code must be a string"
    assert len(zip_code) == 5 and zip_code.isdigit(), "Zip code must be a 5-digit number"
    url = f"https://nominatim.openstreetmap.org/search?postalcode={zip_code}&country=US&format=json"
    headers = {'User-Agent': 'llm-fm/1.0'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        assert data, f"No data received for zip code: {zip_code}"
        if data:
            lat = float(data[0]['lat'])
            lon = float(data[0]['lon'])
            assert -90 <= lat <= 90, f"Latitude {lat} is out of range"
            assert -180 <= lon <= 180, f"Longitude {lon} is out of range"
            return lat, lon
        else:
            raise ValueError(f"Could not find location for zip code: {zip_code}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Nominatim API request failed: {e}")
        raise
    except (KeyError, ValueError, TypeError) as e:
        logging.error(f"Error parsing Nominatim data: {e}")
        raise

def fetch_weather_data(lat, lon):
    """Fetches weather data from the National Weather Service API."""
    try:
        # Get the station data
        station_url = f"https://api.weather.gov/points/{lat},{lon}"
        station_response = requests.get(station_url)
        station_response.raise_for_status()
        station_data = station_response.json()

        # Extract hourly forecast URL
        hourly_forecast_url = station_data['properties']['forecastHourly']

        # Get the hourly forecast
        hourly_response = requests.get(hourly_forecast_url)
        hourly_response.raise_for_status()
        hourly_data = hourly_response.json()

        city = station_data['properties']['relativeLocation']['properties']['city']
        state = station_data['properties']['relativeLocation']['properties']['state']

        return hourly_data, city, state

    except requests.exceptions.RequestException as e:
        logging.error(f"Weather API request failed: {e}")
        return None, None, None
    except (KeyError, ValueError, TypeError) as e:
        logging.error(f"Error parsing weather data: {e}")
        return None, None, None

def get_current_forecast(hourly_data):
    """Extracts the current hourly forecast."""
    if not hourly_data or 'properties' not in hourly_data or 'periods' not in hourly_data['properties']:
        logging.error("Invalid hourly data.")
        return None

    now = datetime.now()
    current_hour = now.strftime("%Y-%m-%dT%H")
    
    for period in hourly_data['properties']['periods']:
        start_time = period['startTime']
        if current_hour in start_time:
            return period
    return None

def format_weather_prompt(city, state, curdate, forecast):
    """Formats the weather prompt for the LLM."""
    return (f"We are in {city}, {state}. The current date is ```{curdate}```. "
            f"The hourly forecast in JSON is ```{json.dumps(forecast)}```. "
            "Please provide a friendly and concise weather report based on the forecast. "
            "Focus only on the weather for the upcoming hour and keep the report engaging. "
            "Avoid making any predictions or comments about hours beyond the current one. "
            "Write all numbers and abbreviations as words, for example instead of '10:51' is 'ten fifty-one'.")

def get_llm_weather_report(city, state, curdate, forecast):
     """Gets the weather report from the LLM."""
     system_prompt = "You are a meteorologist. The Weather Station is LLM, Large Language Meteorology."
     user_prompt = format_weather_prompt(city, state, curdate, forecast)
     weather_report = llm_call(system_prompt, user_prompt)
     return weather_report

def llm_call(system_prompt, user_prompt):
    """Makes a call to the LLM and returns the response."""
    assert isinstance(system_prompt, str), "System prompt must be a string"
    assert isinstance(user_prompt, str), "User prompt must be a string"
    headers = {"Content-Type": "application/json"}
    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": TEMPERATURE,
    }
    try:
        response = requests.post(f"{BASE_URL}/chat/completions", headers=headers, json=data, stream=False)
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']
        assert isinstance(content, str) and content, "LLM response must be a non-empty string"
        print(f"Raw LLM Response: {content}")

        match = re.search(r"```json\n(.*)```", content, re.DOTALL)
        if match:
            json_string = match.group(1)
            return json_string
        else:
            return content
    except requests.exceptions.RequestException as e:
        logging.error(f"LLM call failed: {e}")
        return None
    except (KeyError, ValueError) as e:
        logging.error(f"Error parsing LLM response: {e}")
        return None

def speak(text):
    """Speaks the given text using pyttsx3."""
    assert isinstance(text, str), "Text must be a string"
    try:
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        logging.error(f"pyttsx3 failed: {e}")

def play_audio(song):
    """Plays audio from YouTube using yt-dlp and mpv."""
    global mpv_process
    assert isinstance(song, str), "Song must be a string"
    try:
        url = subprocess.check_output(["yt-dlp", "--no-warnings", "--quiet", "-x", "-g", f"ytsearch:{song}"]).decode('utf-8').strip()
        mpv_process = subprocess.Popen(
            ["mpv", "--no-video", url]
        )
        assert mpv_process is not None, "mpv_process must not be None"
        return mpv_process
    except subprocess.CalledProcessError as e:
        logging.error(f"yt-dlp or mpv failed: {e}")
        return None

def fix_quotes(json_string):
    """Replaces curly quotes with straight quotes in a JSON string."""
    assert isinstance(json_string, str), "JSON string must be a string"
    json_string = json_string.replace("“", "\"")
    json_string = json_string.replace("”", "\"")
    return json_string

def get_dj_info(genre, last_played):
    """Gets the DJ information from the LLM."""
    assert isinstance(genre, str), "Genre must be a string"
    assert isinstance(last_played, list), "last_played must be a list"
    curdate = time.strftime("%a %b %d %Y %H:%M %p")
    system_prompt = f"You are a {genre} radio DJ."
    user_prompt = (
        "Pick a song that you want to play next and add a short description to lead into the song. "
        "Output this in JSON. Only include the fields for the 'song' and 'description'. Use the JSON format. "
        "The song should be in 'Song_Name - Artist' format. The current date is {}.".format(curdate) +
        f"You've already played these tracks (most recent first) ```{last_played}``` NEVER replay them!"
    )
    dj_info = llm_call(system_prompt, user_prompt)
    assert dj_info is not None, "LLM returned None"
    return dj_info

def parse_dj_info(dj_info):
    """Parses the DJ information from the LLM response."""
    assert isinstance(dj_info, str), "dj_info must be a string"
    dj_info = fix_quotes(dj_info)
    try:
        dj_data = json.loads(dj_info)
        assert isinstance(dj_data, dict), "dj_data must be a dict"
        song = dj_data.get('song')
        desc = dj_data.get('description')
        return song, desc
    except (json.JSONDecodeError, TypeError) as e:
        logging.error(f"Error parsing LLM response: {e}")
        return None, None

def announce_song(desc, song):
    """Announces the song and description."""
    assert isinstance(desc, str) and desc, "Description must be a non-empty string"
    assert isinstance(song, str) and song, "Song must be a non-empty string"
    print(desc)
    speak(desc)
    print(f"Next Up: {song}")
    speak(f"Next Up: {song}")

def manage_last_played(song, last_played):
    """Manages the last played list."""
    assert isinstance(song, str) and song, "Song must be a non-empty string"
    assert isinstance(last_played, list), "last_played must be a list"

    print(f"(Last Played was: {last_played})")
    last_played.insert(0, song)
    if len(last_played) > MAX_LAST_PLAYED:
        last_played.pop()
    return last_played

def get_weather_and_announce(lat, lon):
    """Gets the weather forecast and announces it."""
    try:
        curdate = time.strftime("%a %b %d %Y %H:%M %p")
        hourly_data, city, state = fetch_weather_data(lat, lon)

        if not hourly_data or not city or not state:
            logging.warning("Could not retrieve weather data.")
            return

        forecast = get_current_forecast(hourly_data)
        if not forecast:
            logging.warning("Could not retrieve current forecast.")
            return

        weather_report = get_llm_weather_report(city, state, curdate, forecast)
        if not weather_report:
            logging.warning("Could not retrieve weather report from LLM.")
            return

        print(f"Local Weather Report: {weather_report}")
        speak(weather_report)

    except Exception as e:
        logging.error(f"Error in get_weather_and_announce: {e}")

def send_mpv_command(command):
    """Sends a command to the mpv instance via its IPC socket."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(MPV_SOCKET)
            command_json = json.dumps({"command": command}) + "\n"
            sock.sendall(command_json.encode())
            logging.info(f"Sent command to mpv: {command}")
    except socket.error as e:
        logging.error(f"Could not send command to mpv: {e}")

def main_loop(genre, lat, lon):
    """Main loop to run the radio DJ."""
    global last_played, exiting, mpv_process
    runs = 0

    while not exiting and runs < MAX_RUNS:
        try:
            dj_info = get_dj_info(genre, last_played)
            song, desc = parse_dj_info(dj_info)

            if not song or not desc:
                logging.warning("Could not extract song and description from LLM response.")
                time.sleep(10)
                continue

            if song in last_played:
                print(f"Skipping already played song: {song}")
                time.sleep(5)
                continue

            announce_song(desc, song)

            print(f"(Last Played was: {last_played})")
            mpv_process = play_audio(song)
            if mpv_process:
                mpv_process.wait()

            last_played = manage_last_played(song, last_played)

            if runs % 5 == 0:
                get_weather_and_announce(lat, lon)

            runs += 1
            time.sleep(3)
        except Exception as e:
            logging.error(f"Error in main loop: {e}")
            time.sleep(10)  # Wait before retrying after an error

    print("Exiting main loop.")

def main():
    """Main function to run the radio DJ."""
    global exiting, mpv_process

    parser = argparse.ArgumentParser(description="LLM-FM: A radio DJ powered by a language model.")
    parser.add_argument("genre", nargs='?', default="Pop", help="The genre of music for the radio station.")
    args = parser.parse_args()
    genre = args.genre

    try:
        lat, lon = get_location_from_zip(ZIP_CODE)
    except ValueError as e:
        print(e)
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Failed to get location data: {e}")
        sys.exit(1)

    def signal_handler(sig, frame):
        global exiting, mpv_process
        if exiting:
            return  # Prevent re-entering the handler

        exiting = True
        print("Cleaning up and exiting...")

        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    main_loop(genre, lat, lon)
    print("Exiting.")

if __name__ == "__main__":
    main()
