#!/usr/bin/env python3

import os
import sys
import subprocess
import xml.etree.ElementTree as ET
import json
import requests
from datetime import datetime
import tempfile
import llm_rottentomatoes
import shutil

# Configuration (Move to a config file or environment variables later)
PLEX_URL = "http://plex.lan"
import getpass
PLEX_LIBRARY_SECTION = "1"  # Movies
LLM_BASE_URL = "http://localhost:9090/v1"
LLM_MODEL = "llama-3.2-3b-it-q8_0"
DEFAULT_TEMPERATURE = 0.7
ROTTEN_TOMATOES_URL = "https://www.rottentomatoes.com/browse/movies_at_home/sort:popular"
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'

def get_plex_genres(api_key):
    """Fetches movie genres from Plex."""
    url = f"{PLEX_URL}/library/sections/{PLEX_LIBRARY_SECTION}/genre?X-Plex-Token={api_key}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        xml_content = response.text
        root = ET.fromstring(xml_content)
        genres = [(d.get('key'), d.get('title')) for d in root.findall('Directory')]
        return genres
    except requests.exceptions.RequestException as e:
        print(f"Error fetching genres from Plex: {e}")
        sys.exit(1)
    except ET.ParseError as e:
        print(f"Error parsing XML from Plex: {e}")
        sys.exit(1)

def get_plex_movies_by_genre(api_key, genre_id):
    """Fetches movies of a specific genre from Plex."""
    url = f"{PLEX_URL}/library/sections/{PLEX_LIBRARY_SECTION}/genre/{genre_id}?X-Plex-Token={api_key}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        xml_content = response.text
        root = ET.fromstring(xml_content)
        movies = []
        for video in root.findall('Video'):
            movie = {
                'Title': video.get('title'),
                'rating': video.get('rating'),
                'audienceRating': video.get('audienceRating'),
                'year': video.get('year'),
                'summary': video.get('summary'),
                'Director': [d.get('tag') for d in video.findall('Director')],
                'Genre': [g.get('tag') for g in video.findall('Genre')]
            }
            movies.append(movie)
        return movies
    except requests.exceptions.RequestException as e:
        print(f"Error fetching movies by genre from Plex: {e}")
        sys.exit(1)
    except ET.ParseError as e:
        print(f"Error parsing XML from Plex: {e}")
        sys.exit(1)

def get_plex_unwatched_movies(api_key):
    """Fetches unwatched movies from Plex."""
    url = f"{PLEX_URL}/library/sections/{PLEX_LIBRARY_SECTION}/unwatched?X-Plex-Token={api_key}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        xml_content = response.text
        root = ET.fromstring(xml_content)
        movies = []
        for video in root.findall('Video'):
            movie = {
                'Title': video.get('title'),
                'rating': video.get('rating'),
                'audienceRating': video.get('audienceRating'),
                'year': video.get('year'),
                'summary': video.get('summary'),
                'Director': [d.get('tag') for d in video.findall('Director')],
                'Genre': [g.get('tag') for g in video.findall('Genre')]
            }
            movies.append(movie)
        return movies
    except requests.exceptions.RequestException as e:
        print(f"Error fetching unwatched movies from Plex: {e}")
        sys.exit(1)
    except ET.ParseError as e:
        print(f"Error parsing XML from Plex: {e}")
        sys.exit(1)

def get_all_plex_movies(api_key):
    """Fetches all movies from Plex."""
    url = f"{PLEX_URL}/library/sections/{PLEX_LIBRARY_SECTION}/all?X-Plex-Token={api_key}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        xml_content = response.text
        root = ET.fromstring(xml_content)
        movies = []
        for video in root.findall('Video'):
            movie = {
                'Title': video.get('title'),
                'rating': video.get('rating'),
                'audienceRating': video.get('audienceRating'),
                'year': video.get('year'),
                'summary': video.get('summary'),
                'Director': [d.get('tag') for d in video.findall('Director')],
                'Genre': [g.get('tag') for g in video.findall('Genre')]
            }
            movies.append(movie)
        return movies
    except requests.exceptions.RequestException as e:
        print(f"Error fetching all movies from Plex: {e}")
        sys.exit(1)
    except ET.ParseError as e:
        print(f"Error parsing XML from Plex: {e}")
        sys.exit(1)

def scrape_rotten_tomatoes():
    """Scrapes movie information from Rotten Tomatoes."""
    try:
        response = requests.get(ROTTEN_TOMATOES_URL, headers={'User-Agent': USER_AGENT})
        response.raise_for_status()
        html_content = response.text

        # Extract JSON data using string manipulation (safer than regex in this case)
        start_marker = '{"audienceScore'
        end_marker = '</script>'
        start_index = html_content.find(start_marker)
        end_index = html_content.find(end_marker, start_index)

        if start_index == -1 or end_index == -1:
            print("Could not find Rotten Tomatoes data on the page.")
            return []

        json_string = html_content[start_index:end_index].rsplit(';', 1)[0]

        # Load the JSON data
        data = json.loads(json_string)
        movies = []
        movie_data = {
            'Film Title': data.get('title', ''),
            'Critic Rating': data.get('criticsScore', {}).get('rating', ''),
            'Critic Sentiment': data.get('criticsScore', {}).get('sentiment', ''),
            'Audience Rating': data.get('audienceScore', {}).get('score', ''),
            'Audience Sentiment': data.get('audienceScore', {}).get('sentiment', ''),
            'Director': ', '.join(data.get('director', [])),
            'Actors': ', '.join(data.get('actor', [])),
            'Description': data.get('description', '')
        }
        movies.append(movie_data)
        return movies

    except requests.exceptions.RequestException as e:
        print(f"Error fetching Rotten Tomatoes data: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from Rotten Tomatoes: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred while scraping Rotten Tomatoes: {e}")
        return []

def llm_query(system_prompt, user_content, temperature=DEFAULT_TEMPERATURE):
    """Queries the LLM with a system prompt and user content."""
    try:
        response = requests.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers={"Content-Type": "application/json"},
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                "temperature": temperature,
                "stream": False,
            },
            timeout=3600  # Timeout in seconds
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()
    except requests.exceptions.RequestException as e:
        print(f"Error querying LLM: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from LLM: {e}")
        return None

def llm_query_with_rt(system_prompt, plex_movies, rotten_tomatoes_movies, temperature=DEFAULT_TEMPERATURE):
    """Queries the LLM with Plex movies and Rotten Tomatoes data."""
    plex_movies_str = format_plex_movies(plex_movies)
    rotten_tomatoes_str = format_rotten_tomatoes_movies(rotten_tomatoes_movies)

    user_content = f"Plex Movies:\n{plex_movies_str}\n\nRotten Tomatoes Movies:\n{rotten_tomatoes_str}"

    return llm_query(system_prompt, user_content, temperature)

def format_plex_movies(movies):
    """Formats Plex movie data into a string."""
    output = ""
    for movie in movies:
        output += f"Title: `{movie['Title']}` "
        output += f"RottenTomatoes Critic Rating: `{movie['rating']}` "
        output += f"Audience Rating: `{movie['audienceRating']}` "
        output += f"Year: `{movie['year']}` "
        output += f"Summary: `{movie['summary']}` "
        output += f"Director: `{', '.join(movie['Director'])}` "
        output += f"Genre: `{', '.join(movie['Genre'])}`\n"
    return output

def format_rotten_tomatoes_movies(movies):
    """Formats Rotten Tomatoes movie data into a string."""
    output = ""
    for movie in movies:
        output += f"Film Title: `{movie['Film Title']}` "
        output += f"Critic Rating: `{movie['Critic Rating']}%/100% and is {movie['Critic Sentiment']} ` "
        output += f"Audience Rating: `{movie['Audience Rating']}%/100% and is {movie['Audience Sentiment']} ` "
        output += f"Director: `{movie['Director']}` "
        output += f"Actors: `{movie['Actors']}` "
        output += f"Description: `{movie['Description']}`\n"
    return output

def main():
    """Main function to orchestrate movie recommendations."""
    api_key = os.environ.get("PLEX_API_KEY")
    if not api_key:
        api_key = getpass.getpass("Please enter your Plex API key: ")

    current_date = datetime.now().strftime("%a %b %d %Y %H:%M %p")
    temperature = DEFAULT_TEMPERATURE

    # Genre Recommendation
    genres = get_plex_genres(api_key)
    if genres:
        genre_names = [genre[1] for genre in genres]
        genre_list_str = "\n".join(genre_names)
        system_prompt = f"You are a movie expert. The current date is {current_date}"
        preprompt = "The following are the available movie genres we can select from:"
        postprompt = "What genre should we pick? Output your selection in JSON format and do not give any explanation."
        llm_response = llm_query(system_prompt, f"{preprompt}\n{genre_list_str}\n{postprompt}", temperature)

        if llm_response:
            try:
                genre_selection = json.loads(llm_response)['genre']
                print(f"------------{genre_selection} Suggestion------------")
                # Find the genre ID
                genre_id = next((genre[0] for genre in genres if genre[1].lower() == genre_selection.lower()), None)
                if genre_id:
                    movies = get_plex_movies_by_genre(api_key, genre_id)
                    if movies:
                        movie_list_str = format_plex_movies(movies)
                        system_prompt = f"You are a movie expert. The current date is {current_date}"
                        preprompt = f"The following is the list of `{genre_selection}` movies that are available to play:"
                        postprompt = "Based on that list what movie should I watch next? Output only your top selection based on your expertise."
                        llm_response = llm_query(system_prompt, f"{preprompt}\n{movie_list_str}\n{postprompt}", temperature)
                        if llm_response:
                            print(llm_response)
                    else:
                        print(f"No movies found for genre: {genre_selection}")
                else:
                    print(f"Genre ID not found for genre: {genre_selection}")
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error processing LLM response for genre: {e}")
        else:
            print("Failed to get genre recommendation from LLM.")
    else:
        print("No genres found on Plex.")

    # Unwatched Recommendation
    print("------------Unwatched Suggestion------------")
    unwatched_movies = get_plex_unwatched_movies(api_key)
    if unwatched_movies:
        movie_list_str = format_plex_movies(unwatched_movies)
        system_prompt = f"You are a movie expert. The current date is {current_date}"
        preprompt = "The following is the list of movies that are available to watch:"
        postprompt = "Based on that list what movie should I watch next? Output only your top selection based on your expertise."
        llm_response = llm_query(system_prompt, f"{preprompt}\n{movie_list_str}\n{postprompt}", temperature)
        if llm_response:
            print(llm_response)
        else:
            print("Failed to get unwatched movie recommendation from LLM.")
    else:
        print("No unwatched movies found on Plex.")

    # Rotten Tomatoes Recommendation
    print("------------RottenTomatoes Suggestion------------")
    all_movies = get_all_plex_movies(api_key)
    rotten_tomatoes_movies = llm_rottentomatoes.scrape_rotten_tomatoes()

    if all_movies and rotten_tomatoes_movies:
        system_prompt = f"You are a movie expert. The current date is {current_date}"
        preprompt1 = "The following is the user's current movie collection:"
        postprompt1 = "The following are the current Movie Releases:"
        postprompt2 = "Of the current movie releases, which ones fit the user's movie tastes the most and why?"
        llm_response = llm_query_with_rt(system_prompt, all_movies, rotten_tomatoes_movies, temperature)
        if llm_response:
            print(llm_response)
        else:
            print("Failed to get Rotten Tomatoes movie recommendation from LLM.")
    else:
        print("Could not retrieve all movies from Plex or Rotten Tomatoes data.")

if __name__ == "__main__":
    main()
