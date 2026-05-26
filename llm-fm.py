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
import random
from datetime import datetime
import logging
import socket

load_dotenv()

# Configuration
ZIP_CODE = os.getenv("ZIP_CODE")
TEMPERATURE = 1.0
MODEL = "gemma-3-4b-it-q8_0"
BASE_URL = os.getenv("BASE_URL")
API_KEY = "None"
ESPEAK_SPEED = 160
YT_DLP_FORMAT = "bestaudio/best"
MAX_LAST_PLAYED = 100  # Maximum number of songs to keep in last_played list
MAX_RUNS = 1000 # Maximum runs before exiting.  Remove for infinite loop.
MPV_SOCKET = "/dev/shm/mpv_socket"
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")
LASTFM_BASE_URL = "http://ws.audioscrobbler.com/2.0/"
MAX_SIMILAR_TRACKS = 10

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize pyttsx3
engine = pyttsx3.init()
engine.setProperty('rate', ESPEAK_SPEED)

last_played = []
exiting = False  # Global flag to prevent re-entering the signal handler
mpv_process = None # Global variable to store the mpv process
DEBUG = False

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

    if DEBUG:
        print(f"\n--- LLM SYSTEM PROMPT ---\n{system_prompt}\n")
        print(f"--- LLM USER PROMPT ---\n{user_prompt}\n")

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
        # Split on dash and use both parts for ytsearch to ensure both title and artist are included
        if ' - ' in song:
            song_title = song.split(' - ')[0].strip()
            artist = song.split(' - ')[1].strip()
            search_query = f"{song_title} {artist}"
        else:
            search_query = song
        url = subprocess.check_output(["yt-dlp", "--no-warnings", "--quiet", "-x", "-g", f"ytsearch:{search_query}"]).decode('utf-8').strip()
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
    json_string = json_string.replace("\u201c", "\"")
    json_string = json_string.replace("\u201d", "\"")
    return json_string

def get_similar_tracks(artist, track):
    """Fetches similar tracks from the Last.fm API."""
    if not LASTFM_API_KEY:
        if DEBUG:
            print("DEBUG: Skipping Last.fm — LASTFM_API_KEY not set.")
        return []
    assert isinstance(artist, str), "Artist must be a string"
    assert isinstance(track, str), "Track must be a string"

    params = {
        'method': 'track.getsimilar',
        'artist': artist,
        'track': track,
        'api_key': LASTFM_API_KEY,
        'format': 'json',
        'limit': MAX_SIMILAR_TRACKS,
        'autocorrect': 1,
    }

    if DEBUG:
        print(f"DEBUG: Fetching similar tracks for artist='{artist}' track='{track}'")
        print(f"DEBUG: Last.fm URL: {LASTFM_BASE_URL}?method=track.getsimilar&artist={artist}&track={track}&api_key=***&format=json&limit={MAX_SIMILAR_TRACKS}&autocorrect=1")

    try:
        response = requests.get(LASTFM_BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()

        if DEBUG:
            if 'error' in data:
                print(f"DEBUG: Last.fm error response: {data}")
            elif 'similartracks' in data:
                track_count = len(data['similartracks'].get('track', [])) if isinstance(data['similartracks'].get('track'), list) else 1
                print(f"DEBUG: Last.fm returned {track_count} similar tracks")

        if 'similartracks' not in data or 'track' not in data['similartracks']:
            logging.warning("Last.fm returned no similar tracks.")
            return []

        raw_tracks = data['similartracks']['track']
        if not isinstance(raw_tracks, list):
            raw_tracks = [raw_tracks]

        tracks = []
        for t in raw_tracks:
            tracks.append({
                'song': f"{t['name']} - {t['artist']['name']}",
                'match': float(t['match'])
            })
        return tracks

    except requests.exceptions.RequestException as e:
        logging.error(f"Last.fm API request failed: {e}")
        if DEBUG:
            print(f"DEBUG: Last.fm request exception: {e}")
        return []
    except (KeyError, ValueError, TypeError) as e:
        logging.error(f"Error parsing Last.fm response: {e}")
        if DEBUG:
            print(f"DEBUG: Last.fm parse exception: {e}")
        return []

def get_track_genre(artist, track):
    """Fetches the top genre tag for a track from Last.fm, falling back to artist tags."""
    if not LASTFM_API_KEY:
        return None
    assert isinstance(artist, str), "Artist must be a string"
    assert isinstance(track, str), "Track must be a string"

    params = {
        'api_key': LASTFM_API_KEY,
        'artist': artist,
        'track': track,
        'format': 'json',
        'autocorrect': 1,
    }

    try:
        params['method'] = 'track.getInfo'
        response = requests.get(LASTFM_BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        tags = data.get('track', {}).get('toptags', {}).get('tag', [])
        if tags and isinstance(tags, list) and len(tags) > 0:
            genre = tags[0].get('name', '').strip()
            if genre:
                if DEBUG:
                    print(f"DEBUG: Genre from track tags: '{genre}'")
                return genre

        if DEBUG:
            print("DEBUG: No track tags, falling back to artist tags...")

        artist_params = {
            'method': 'artist.getTopTags',
            'api_key': LASTFM_API_KEY,
            'artist': artist,
            'format': 'json',
            'autocorrect': 1,
        }
        response = requests.get(LASTFM_BASE_URL, params=artist_params)
        response.raise_for_status()
        data = response.json()
        tags = data.get('toptags', {}).get('tag', [])
        if tags and isinstance(tags, list) and len(tags) > 0:
            genre = tags[0].get('name', '').strip()
            if genre:
                if DEBUG:
                    print(f"DEBUG: Genre from artist tags: '{genre}'")
                return genre

        logging.warning(f"Last.fm returned no genre tags for artist='{artist}' track='{track}'")
        return None

    except requests.exceptions.RequestException as e:
        logging.error(f"Last.fm genre lookup failed: {e}")
        return None
    except (KeyError, ValueError, TypeError, IndexError) as e:
        logging.error(f"Error parsing Last.fm genre response: {e}")
        return None

def get_genre_from_song(song_string):
    """Parses a 'Song - Artist' string and returns the genre from Last.fm."""
    if ' - ' not in song_string:
        logging.warning(f"Cannot parse artist/track from song string: '{song_string}'")
        return None

    track, artist = song_string.split(' - ', 1)
    genre = get_track_genre(artist.strip(), track.strip())
    if genre:
        print(f"Auto-detected genre from Last.fm: '{genre}' (from track '{track.strip()}' by '{artist.strip()}')")
    return genre

def get_dj_info(genre, last_played, similar_tracks=None):
    """Gets the DJ information from the LLM."""
    assert isinstance(genre, str), "Genre must be a string"
    assert isinstance(last_played, list), "last_played must be a list"
    curdate = time.strftime("%a %b %d %Y %H:%M %p")
    system_prompt = f"You are a {genre} radio DJ."

    if similar_tracks:
        random.shuffle(similar_tracks)
        tracks_list = "\n".join(
            [f"{i+1}. {t['song']}" for i, t in enumerate(similar_tracks)]
        )
        user_prompt = (
            "Pick a song that you want to play next. You may use one of the similar songs below, "
            "or choose a different song if you prefer, and add a short description to lead into the song. "
            "Output this in JSON. Only include the fields for the 'song' and 'description'. Use the JSON format. "
            "The song should be in 'Song_Name - Artist' format. The current date is {}.\n".format(curdate) +
            f"You've already played these tracks (most recent first) ```{last_played}``` NEVER replay them!\n"
            f"Here are similar songs you may choose from (pick ONE):\n{tracks_list}\n"
            "You may pick from the list or suggest a different song in 'Song_Name - Artist' format."
        )
    else:
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
        
        # Remove asterisks from song and description
        if song:
            song = song.replace("*", "")
        if desc:
            desc = desc.replace("*", "")
            
        return song, desc
    except (json.JSONDecodeError, TypeError) as e:
        logging.error(f"Error parsing LLM response: {e}")
        return None, None

def announce_song(desc, song):
    """Announces the song and description."""
    assert isinstance(desc, str) and desc, "Description must be a non-empty string"
    assert isinstance(song, str) and song, "Song must be a non-empty string"
    
    # Remove asterisks from description and song
    desc_clean = desc.replace("*", "")
    song_clean = song.replace("*", "")
    
    print(desc_clean)
    speak(desc_clean)
    print(f"Next Up: {song_clean}")
    speak(f"Next Up: {song_clean}")

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

def main_loop(genre, lat, lon, use_lastfm=False, song_start=None):
    """Main loop to run the radio DJ."""
    global last_played, exiting, mpv_process
    runs = 0

    if song_start:
        use_lastfm = True

    while not exiting and runs < MAX_RUNS:
        try:
            if song_start and runs == 0:
                print(f"Starting with: {song_start}")
                mpv_process = play_audio(song_start)
                if mpv_process:
                    mpv_process.wait()
                last_played = manage_last_played(song_start, last_played)
                runs += 1
                time.sleep(3)
                continue

            similar_tracks = []
            if use_lastfm and last_played:
                last_song = last_played[0]
                if ' - ' in last_song:
                    track, artist = last_song.split(' - ', 1)
                    similar_tracks = get_similar_tracks(artist, track)
                else:
                    similar_tracks = get_similar_tracks('', last_song)

            similar_tracks = [t for t in similar_tracks if t['song'] not in last_played]

            if DEBUG and similar_tracks:
                print(f"DEBUG: Passing {len(similar_tracks)} similar tracks to LLM for selection")

            dj_info = get_dj_info(genre, last_played, similar_tracks if similar_tracks else None)
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

            # Check weather every 5 songs (5th, 10th, 15th, etc.)
            if (runs + 1) % 5 == 0:
                get_weather_and_announce(lat, lon)

            runs += 1
            time.sleep(3)
        except Exception as e:
            logging.error(f"Error in main loop: {e}")
            time.sleep(10)  # Wait before retrying after an error

    print("Exiting main loop.")

def main():
    """Main function to run the radio DJ."""
    global exiting, mpv_process, DEBUG

    parser = argparse.ArgumentParser(description="LLM-FM: A radio DJ powered by a language model.")
    parser.add_argument("genre", nargs='?', default=None, help="The genre of music for the radio station. If omitted and --start-song is used, genre is auto-detected from Last.fm.")
    parser.add_argument("--debug", action="store_true", help="Print LLM prompts and API calls.")
    parser.add_argument("--lastfm", action="store_true",
                        help="Use Last.fm track.getSimilar to seed song choices. Requires LASTFM_API_KEY in .env.")
    parser.add_argument("--song-start", type=str, default=None,
                        help="Starting song in 'Song Title - Artist' format. Enables Last.fm mode and auto-detects genre from the song's Last.fm tags if no genre is given.")
    args = parser.parse_args()
    genre = args.genre
    DEBUG = args.debug
    use_lastfm = args.lastfm
    song_start = args.song_start

    if genre is None and song_start:
        genre = get_genre_from_song(song_start)
    if genre is None:
        genre = "Pop"

    if DEBUG:
        print(f"DEBUG: Using genre='{genre}'")

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

    main_loop(genre, lat, lon, use_lastfm, song_start)
    print("Exiting.")

if __name__ == "__main__":
    main()
