import requests
import json
import os
import time
from time import sleep
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

def retry_request(max_retries=5, delay=5):
    """
    Decorator to retry a function that makes an API request.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.RequestException as e:
                    if e.response is not None and e.response.status_code == 500:
                        print(f"Server Error (500) detected. Retrying in {delay} seconds...")
                        retries += 1
                        time.sleep(delay)
                    else:
                        raise e  # Re-raise exceptions that are not 500 errors
            print(f"Max retries reached. Function {func.__name__} failed.")
            return None  # Or raise an exception, depending on your needs
        return wrapper
    return decorator

class TubeArchivistAPI:
    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url
        self.api_token = api_token

    @retry_request()
    def get_latest_videos(self, page_size=12):
        """Retrieves the latest downloaded videos from the TubeArchivist API."""
        endpoint = f"{self.base_url}/api/video/"
        headers = {"Authorization": f"Token {self.api_token}"}

        response = requests.get(endpoint, headers=headers)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        return data

    @retry_request()
    def get_channel_stats(self):
        """
        Retrieves channel stats from the TubeArchivist API.
        """
        endpoint = f"{self.base_url}/api/stats/channel/"
        headers = {"Authorization": f"Token {self.api_token}"}

        response = requests.get(endpoint, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data

    @retry_request()
    def get_video_stats(self):
        """
        Retrieves video stats from the TubeArchivist API.
        """
        endpoint = f"{self.base_url}/api/stats/video/"
        headers = {"Authorization": f"Token {self.api_token}"}

        response = requests.get(endpoint, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data

    @retry_request()
    def get_biggest_channels(self, order="doc_count"):
        """
        Retrieves the biggest channels stats from the TubeArchivist API.
        """
        endpoint = f"{self.base_url}/api/stats/biggestchannels/?order={order}"
        headers = {"Authorization": f"Token {self.api_token}"}

        response = requests.get(endpoint, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data

    def get_all_videos(self, page_size=5):
        """Retrieves all videos from the TubeArchivist API, paginating through all pages."""
        all_videos = []
        page = 1
        while True:
            endpoint = f"{self.base_url}/api/video/?page={page}&page_size={page_size}"
            headers = {"Authorization": f"Token {self.api_token}"}
            try:
                response = requests.get(endpoint, headers=headers)
                response.raise_for_status()
                data = response.json()
                if "data" in data and isinstance(data["data"], list):
                    for video in data["data"]:
                        if "youtube_id" in video:
                            has_subtitles = "subtitles" in video and video["subtitles"]
                            if has_subtitles:
                                print(f"{video['youtube_id']} Had Subtitles")
                                sleep(1)
                            else:
                                print(f"{video['youtube_id']} Had NO Subtitles")
                                sleep(1)
                if not data["paginate"]["next_pages"]:
                    break
                page = data["paginate"]["current_page"] + 1
            except requests.exceptions.RequestException as e:
                print(f"Error during get_all_videos pagination: {e}")
                return

    def format_videos(self, videos):
        """
        Formats the video data for more human-readable output.
        """
        formatted_output = []
        for video in videos["data"]:
            formatted_video = {
                "Title": video["title"],
                "Video ID": video["youtube_id"],
                "Description": video["description"],
                "Channel": video["channel"]["channel_name"],
                "Published": video["published"],
                "Duration": video["player"]["duration_str"],
                "Views": video["stats"]["view_count"],
            }
            formatted_output.append(formatted_video)
        return formatted_output

    def format_channels(self, channel_stats):
        """
        Formats the channel data for more human-readable output.
        """
        formatted_channel = {
            "Total Channels": channel_stats["doc_count"],
            "Active Channels": channel_stats["active_true"],
            "Inactive Channels": channel_stats["active_false"],
            "Subscribed Channels": channel_stats["subscribed_true"],
            "Unsubscribed Channels": channel_stats["subscribed_false"],
        }
        return formatted_channel

    @retry_request()
    def get_watch_stats(self):
        """
        Retrieves watch stats from the TubeArchivist API.
        """
        endpoint = f"{self.base_url}/api/stats/watch/"
        headers = {"Authorization": f"Token {self.api_token}"}

        response = requests.get(endpoint, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data

    @retry_request()
    def get_all_tasks(self):
        """Retrieves all tasks from the TubeArchivist API."""
        endpoint = f"{self.base_url}/api/task-name/"
        headers = {"Authorization": f"Token {self.api_token}"}

        response = requests.get(endpoint, headers=headers)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        return data

    @retry_request()
    def get_video(self, video_id: str):
        """Retrieves a specific video's information from the TubeArchivist API."""
        endpoint = f"{self.base_url}/api/video/{video_id}/"
        headers = {"Authorization": f"Token {self.api_token}"}

        response = requests.get(endpoint, headers=headers)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        return data

    def format_tasks(self, tasks):
        """Formats the task data for more human-readable output."""
        formatted_tasks = []
        for task in tasks:
            formatted_task = {
                "Task Name": task["name"],
                "Status": task["status"],
                "Date Done": task["date_done"],
                "Task ID": task["task_id"],
            }
            formatted_tasks.append(formatted_task)
        return formatted_tasks

    def format_search_results(self, search_results):
        """
        Formats the search results into a more human-readable format.
        """
        formatted_videos = []
        if search_results and search_results["results"]["video_results"]:
            for video in search_results["results"]["video_results"]:
                formatted_video = {
                    "Title": video["title"],
                    "Video ID": video["youtube_id"],
                    "Description": video["description"],
                    "Channel": video["channel"]["channel_name"],
                    "Published": video["published"],
                    "Duration": video["player"]["duration_str"],
                    "Views": video["stats"]["view_count"],
                }
                formatted_videos.append(formatted_video)
        return formatted_videos

    @retry_request()
    def search(self, query: str):
        """
        Searches the TubeArchivist API with the given query.
        """
        endpoint = f"{self.base_url}/api/search/?query={query}"
        headers = {"Authorization": f"Token {self.api_token}"}

        response = requests.get(endpoint, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data

def main():
    """
    Main function to interact with the TubeArchivist API.
    """

    BASE_URL = "http://tubearchivist.lan"
    API_TOKEN = os.getenv("API_TOKEN")
    # API interaction logic will go here
    print("TubeArchivist API interaction script")
    print(f"Base URL: {BASE_URL}")

    # Instantiate the TubeArchivistAPI class
    api = TubeArchivistAPI(BASE_URL, API_TOKEN)

    # Call the search method
    search_results = api.search(query="test")
    if search_results:
        print("\nSearch Results:")
        formatted_search_results = api.format_search_results(search_results)
        print(json.dumps(formatted_search_results, indent=4))
    else:
        print("Failed to retrieve search results.")

    # Call the get_all_tasks method
    all_tasks = api.get_all_tasks()
    if all_tasks:
        print("\nAll Tasks:")
        formatted_tasks = api.format_tasks(all_tasks)
        print(json.dumps(formatted_tasks, indent=4))
    else:
        print("Failed to retrieve all tasks.")

    # Call the get_latest_videos method, passing the page_size argument
    latest_videos = api.get_latest_videos()
    #print(f"{latest_videos}")
    if latest_videos:
        print("\nLatest Videos:")
        formatted_videos = api.format_videos(latest_videos)
        print(f"Formatted Videos: {json.dumps(formatted_videos, indent=4)}")
    else:
        print("Failed to retrieve latest videos.")

    channel_stats = api.get_channel_stats()
    if channel_stats:
        print("\nChannel Stats:")
        formatted_channels = api.format_channels(channel_stats)
        print(json.dumps(formatted_channels, indent=4))
    else:
        print("Failed to retrieve channel stats.")

    biggest_channels = api.get_biggest_channels()
    if biggest_channels:
        print("\nBiggest Channels:")
        print(json.dumps(biggest_channels, indent=4))
    else:
        print("Failed to retrieve biggest channels.")

    video_stats = api.get_video_stats()
    if video_stats:
        print("\nVideo Stats:")
        print(json.dumps(video_stats, indent=4))
    else:
        print("Failed to retrieve video stats.")

    watch_stats = api.get_watch_stats()
    if watch_stats:
        print("\nWatch Stats:")
        print(json.dumps(watch_stats, indent=4))
    else:
        print("Failed to retrieve watch stats.")

    # Find videos without subtitles
    api.get_all_videos()
    


if __name__ == "__main__":
    main()
