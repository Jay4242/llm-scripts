import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

class TubeArchivistAPI:
    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url
        self.api_token = api_token

    def get_latest_videos(self, page_size=12):
        """Retrieves the latest downloaded videos from the TubeArchivist API."""
        endpoint = f"{self.base_url}/api/video/?page_size={page_size}"
        headers = {"Authorization": f"Token {self.api_token}"}

        try:
            response = requests.get(endpoint, headers=headers)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return None

    def get_channel_stats(self):
        """
        Retrieves channel stats from the TubeArchivist API.
        """
        endpoint = f"{self.base_url}/api/stats/channel/"
        headers = {"Authorization": f"Token {self.api_token}"}

        try:
            response = requests.get(endpoint, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return None

    def get_biggest_channels(self, order="doc_count"):
        """
        Retrieves the biggest channels stats from the TubeArchivist API.
        """
        endpoint = f"{self.base_url}/api/stats/biggestchannels/?order={order}"
        headers = {"Authorization": f"Token {self.api_token}"}

        try:
            response = requests.get(endpoint, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return None

    def format_videos(self, videos):
        """
        Formats the video data for more human-readable output.
        """
        formatted_output = []
        for video in videos["data"]:
            formatted_video = {
                "Title": video["title"],
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

    # Call the get_latest_videos method, passing the page_size argument
    latest_videos = api.get_latest_videos()
    channel_stats = api.get_channel_stats()
    biggest_channels = api.get_biggest_channels()

    if latest_videos:
        print("Latest Videos:")
        formatted_videos = api.format_videos(latest_videos)
        print(f"Formatted Videos: {json.dumps(formatted_videos, indent=4)}")
    else:
        print("Failed to retrieve latest videos.")

    if channel_stats:
        print("\nChannel Stats:")
        formatted_channels = api.format_channels(channel_stats)
        print(json.dumps(formatted_channels, indent=4))
    else:
        print("Failed to retrieve channel stats.")

    if biggest_channels:
        print("\nBiggest Channels:")
        print(json.dumps(biggest_channels, indent=4))
    else:
        print("Failed to retrieve biggest channels.")

if __name__ == "__main__":
    main()
