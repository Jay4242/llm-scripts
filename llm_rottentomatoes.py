#!/usr/bin/env python3

import os
import json
import requests
from bs4 import BeautifulSoup

def scrape_rotten_tomatoes():
    """Scrapes movie information from Rotten Tomatoes."""
    rotten_tomatoes_url = "https://www.rottentomatoes.com/browse/movies_at_home/sort:popular"
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'

    try:
        response = requests.get(rotten_tomatoes_url, headers={'User-Agent': user_agent})
        response.raise_for_status()
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')

        # Find the script tag containing the JSON data
        script_tag = soup.find('script', {'data-hydration-key': 'MOVIES_BROWSE_PAGE'})
        if not script_tag:
            print("Could not find the script tag containing movie data.")
            return []

        # Extract the JSON data
        json_text = script_tag.string
        if not json_text:
            print("Could not extract JSON data from the script tag.")
            return []

        # Load the JSON data
        try:
            data = json.loads(json_text)
            items = data['props']['pageProps']['browserModel']['items']
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Error parsing JSON data: {e}")
            return []

        movies = []
        for item in items:
            try:
                name = item.get('title', '')
                critic_rating = item.get('tomatoScore', {}).get('value', '') if item.get('tomatoScore') else ''
                critic_sentiment = item.get('tomatoScore', {}).get('sentiment', '') if item.get('tomatoScore') else ''
                audience_rating = item.get('audienceScore', {}).get('value', '') if item.get('audienceScore') else ''
                audience_sentiment = item.get('audienceScore', {}).get('sentiment', '') if item.get('audienceScore') else ''
                directors = ', '.join([d['name'] for d in item.get('directors', [])]) if item.get('directors') else ''
                actors = ', '.join([a['name'] for a in item.get('actors', [])]) if item.get('actors') else ''
                description = item.get('synopsis', '')

                movie_data = {
                    'Film Title': name,
                    'Critic Rating': f"{critic_rating}%" if critic_rating else 'N/A',
                    'Critic Sentiment': critic_sentiment or 'N/A',
                    'Audience Rating': f"{audience_rating}%" if audience_rating else 'N/A',
                    'Audience Sentiment': audience_sentiment or 'N/A',
                    'Director': directors or 'N/A',
                    'Actors': actors or 'N/A',
                    'Description': description or 'N/A'
                }
                movies.append(movie_data)
            except Exception as e:
                print(f"Error processing movie item: {e}")
                continue

        return movies

    except requests.exceptions.RequestException as e:
        print(f"Error fetching Rotten Tomatoes data: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []

if __name__ == "__main__":
    movies = scrape_rotten_tomatoes()
    for movie in movies:
        print(f"Film Title: {movie['Film Title']} | Critic Rating: {movie['Critic Rating']} and is {movie['Critic Sentiment']} | Audience Rating: {movie['Audience Rating']} and is {movie['Audience Sentiment']} | Director: {movie['Director']} | Actors: {movie['Actors']} | Description: {movie['Description']}")
