import requests
from bs4 import BeautifulSoup
import json

def scrape_rotten_tomatoes(url="https://www.rottentomatoes.com/browse/movies_at_home/sort:popular"):
    """
    Scrapes movie data from Rotten Tomatoes.

    Args:
        url (str, optional): The URL to scrape. Defaults to Rotten Tomatoes popular streaming movies.

    Returns:
        list: A list of dictionaries, where each dictionary contains movie information.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')
    movie_list = []

    try:
        movie_containers = soup.select('div.discovery-tiles')
        if not movie_containers:
            print("Error: Could not find movie containers.")
            return None

        for container in movie_containers:
            movies = container.select('div.flex-container')
            if not movies:
                print("Error: Could not find movies within container.")
                continue

            for movie in movies:
                title_element = movie.select_one('span.p--small')
                title = title_element.text.strip() if title_element else "N/A"

                score_pairs_element = movie.select_one('score-pairs-deprecated')

                if score_pairs_element:
                    critic_score_element = score_pairs_element.select_one('rt-text[slot="criticsScore"]')
                    audience_score_element = score_pairs_element.select_one('rt-text[slot="audienceScore"]')

                    critic_score = critic_score_element.text.strip() if critic_score_element else "N/A"
                    audience_score = audience_score_element.text.strip() if audience_score_element else "N/A"
                else:
                    critic_score = "N/A"
                    audience_score = "N/A"
                    
                streaming_date_element = movie.select_one('span.smaller')
                streaming_date = streaming_date_element.text.strip() if streaming_date_element else "N/A"

                # Extract the movie URL
                movie_url = movie.select_one('a[data-track="scores"]')
                movie_url = "https://www.rottentomatoes.com" + movie_url['href'] if movie_url and movie_url.has_attr('href') else "N/A"

                movie_info = {
                    'title': title,
                    'critic_score': critic_score,
                    'audience_score': audience_score,
                    'streaming_date': streaming_date,
                    'movie_url': movie_url,  # Add the movie URL to the dictionary
                }
                movie_list.append(movie_info)
    except Exception as e:
        print(f"Error during scraping: {e}")
        return None

    return movie_list

def scrape_movie_details(movie_url):
    """
    Scrapes details from a specific movie page on Rotten Tomatoes.

    Args:
        movie_url (str): The URL of the movie page.

    Returns:
        dict: A dictionary containing movie details, or None if an error occurs.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(movie_url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching movie details from {movie_url}: {e}")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')
    movie_details = {}

    try:
        # Extract description from meta tag
        description_element = soup.find('meta', {'name': 'description'})
        movie_details['description'] = description_element['content'].strip() if description_element and 'content' in description_element.attrs else "N/A"

        # Extract genre, rating, actors, and directors from ld+json
        ld_json_script = soup.find('script', {'type': 'application/ld+json'})
        if ld_json_script:
            ld_json = json.loads(ld_json_script.string)

            movie_details['genre'] = ld_json.get('genre', "N/A")
            movie_details['contentRating'] = ld_json.get('contentRating', "N/A")
            movie_details['actor'] = [actor['name'] for actor in ld_json.get('actor', [])]
            movie_details['director'] = [director['name'] for director in ld_json.get('director', [])]
        else:
            movie_details['genre'] = "N/A"
            movie_details['contentRating'] = "N/A"
            movie_details['actor'] = []
            movie_details['director'] = []

    except Exception as e:
        print(f"Error extracting movie details: {e}")
        return None

    return movie_details

def main():
    movies = scrape_rotten_tomatoes()
    if movies:
        for movie in movies:
            if movie['movie_url'] != "N/A":
                movie_details = scrape_movie_details(movie['movie_url'])
                if movie_details:
                    combined_info = {**movie, **movie_details}
                    print(json.dumps(combined_info))
                else:
                    print(json.dumps({**movie, 'details': 'Could not retrieve details'}))
            else:
                print(json.dumps({**movie, 'details': 'Movie URL not available'}))
    else:
        print("Could not retrieve movie data.")

if __name__ == "__main__":
    main()
