import requests
import json
import os
import time
from time import sleep
from functools import wraps
from dotenv import load_dotenv
import logging
import random
import sys  # Import sys for assertions

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MAX_RETRIES = 3
PAGE_SIZE = 12
BASE_DELAY = 1

def c_assert(condition, message="Assertion failed"):
    """Custom assertion function."""
    if not condition:
        logger.error(f"{message} in {sys._getframe(1).f_code.co_name}")
        return False
    return True

def retry_request(max_retries=MAX_RETRIES, base_delay=BASE_DELAY):
    """Decorator with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    response = func(*args, **kwargs)
                    if response is None:
                        return None
                    return response
                except requests.exceptions.RequestException as e:
                    if e.response and e.response.status_code == 401:
                        logger.error(f"Authentication failed: {e}")
                        return None
                    if e.response and e.response.status_code == 403:
                        logger.error(f"Authorization failed: {e}")
                        return None
                    if e.response and e.response.status_code == 500:
                        delay = base_delay * (2 ** retries) + random.uniform(0, 0.1)
                        logger.info(f"Retrying in {delay:.2f}s...")
                        time.sleep(delay)
                        retries += 1
                    else:
                        raise
            logger.error(f"Max retries reached for {func.__name__}")
            return None
        return wrapper
    return decorator

class TubeArchivistAPI:
    def __init__(self, base_url: str, api_token: str):
        c_assert(isinstance(base_url, str), "base_url must be a string")
        c_assert(isinstance(api_token, str), "api_token must be a string")
        self.base_url = base_url
        self.api_token = api_token

    def _make_request(self, method, endpoint, headers=None, data=None, params=None):
        """Helper method for making authenticated requests."""
        if headers is None:
            headers = {}
        headers["Authorization"] = f"Token {self.api_token}"
        headers["Content-Type"] = "application/json"

        full_url = endpoint
        if params:
            full_url += "?" + "&".join([f"{k}={v}" for k, v in params.items()])
        logger.debug(f"Full Request URL: {full_url}")

        # Redact Authorization header for logging
        log_headers = headers.copy()
        if "Authorization" in log_headers:
            log_headers["Authorization"] = "REDACTED"
        logger.debug(f"Request Headers: {log_headers}")

        try:
            response = method(full_url, headers=headers, data=json.dumps(data), params=params)
            logger.debug(f"Response Status Code: {response.status_code}")
            logger.debug(f"Response Content: {response.content.decode()}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            if e.response is not None:
                logger.error(f"Response status code: {e.response.status_code}")
                logger.error(f"Response content: {e.response.content.decode()}")
            return None

    def _paginate(self, endpoint: str, page_size: int = PAGE_SIZE) -> list:
        """Helper to handle pagination using a loop with a fixed upper bound."""
        all_items = []
        page = 1
        max_pages = 10  # Set a maximum number of pages to prevent infinite loops
        for _ in range(max_pages):
            params = {"page": page, "page_size": page_size}
            response = self._make_request(requests.get, endpoint, params=params)
            if response:
                all_items.extend(response.get("data", []))
                if not response["paginate"].get("next_pages"):
                    break
                page += 1
            else:
                return None
        return all_items

    @retry_request()
    def get_latest_videos(self, page_size=PAGE_SIZE) -> dict | None:
        """Retrieves the latest downloaded videos from the TubeArchivist API."""
        c_assert(isinstance(page_size, int), "page_size must be an integer")
        endpoint = f"{self.base_url}/api/video/"
        return self._make_request(requests.get, endpoint)

    @retry_request()
    def get_video(self, video_id: str) -> dict | None:
        """Retrieves a specific video's information from the TubeArchivist API."""
        c_assert(isinstance(video_id, str), "video_id must be a string")
        endpoint = f"{self.base_url}/api/video/{video_id}/"
        return self._make_request(requests.get, endpoint)

    @retry_request()
    def add_video_to_download_queue(
        self, youtube_id: str, status: str = "pending"
    ) -> dict | None:
        """Adds a video to the download queue with type hints."""
        c_assert(isinstance(youtube_id, str), "youtube_id must be a string")
        c_assert(isinstance(status, str), "status must be a string")
        endpoint = f"{self.base_url}/api/download/bulk_add/"
        data = {"data": [{"youtube_id": youtube_id, "status": status}]}
        return self._make_request(
            requests.post,
            endpoint,
            data=data,
        )

    @retry_request()
    def get_download_queue_list(
        self, filter: str = None, channel: str = None
    ) -> dict | None:
        """Gets the download queue list."""
        if filter:
            c_assert(isinstance(filter, str), "filter must be a string")
        if channel:
            c_assert(isinstance(channel, str), "channel must be a string")
        endpoint = f"{self.base_url}/api/download/"
        params = {}
        if filter:
            params["filter"] = filter
        if channel:
            params["channel"] = channel
        return self._make_request(requests.get, endpoint, params=params)

    @retry_request()
    def get_download_queue_item(self, video_id: str) -> dict | None:
        """Gets a specific download queue item."""
        c_assert(isinstance(video_id, str), "video_id must be a string")
        endpoint = f"{self.base_url}/api/download/{video_id}/"
        return self._make_request(requests.get, endpoint)

    @retry_request()
    def update_download_queue_item(
        self, video_id: str, status: str = None
    ) -> dict | None:
        """Updates a download queue item with validated status."""
        c_assert(isinstance(video_id, str), "video_id must be a string")
        data = {}
        if status:
            c_assert(isinstance(status, str), "status must be a string")
            allowed_statuses = ["pending", "downloading", "completed", "error"]
            c_assert(status in allowed_statuses, f"Invalid status: {status}. Must be one of {allowed_statuses}")
            data["status"] = status
        endpoint = f"{self.base_url}/api/download/{video_id}/"
        return self._make_request(requests.post, endpoint, data=data)

    @retry_request()
    def delete_download_queue_items(self, filter: str) -> dict | None:
        """Deletes download queue items by filter."""
        c_assert(isinstance(filter, str), "filter must be a string")
        endpoint = f"{self.base_url}/api/download/"
        params = {"filter": filter}
        return self._make_request(requests.delete, endpoint, params=params)

    @retry_request()
    def trigger_pending_downloads(self, task_id: str) -> dict | None:
        """Triggers processing of pending download queue items."""
        c_assert(isinstance(task_id, str), "task_id must be a string")
        endpoint = f"{self.base_url}/api/download/process/"
        data = {"task_id": task_id}
        return self._make_request(requests.post, endpoint, data=data)

    def format_videos(self, videos: dict) -> list | None:
        """Formats the video data for more human-readable output."""
        formatted_output = []
        if videos and videos.get("data"):
            video_list = videos["data"]
            max_videos = 100  # Limit the number of videos to format
            for i in range(min(len(video_list), max_videos)):
                video = video_list[i]
                formatted_video = self._format_single_video(video)
                formatted_output.append(formatted_video)
            return formatted_output
        return None

    def _format_single_video(self, video: dict) -> dict:
        """Formats a single video dictionary."""
        c_assert(isinstance(video, dict), "video must be a dictionary")
        formatted_video = {
            "Title": video["title"],
            "Video ID": video["youtube_id"],
            "Description": video["description"],
            "Channel": video["channel"]["channel_name"],
            "Published": video["published"],
            "Duration": video["player"]["duration_str"],
            "Views": video["stats"]["view_count"],
        }
        return formatted_video

    def format_search_results(self, search_results: dict) -> list | None:
        """Formats the search results into a more human-readable format."""
        formatted_videos = []
        if search_results and search_results.get("results") and search_results["results"].get("video_results"):
            video_results = search_results["results"]["video_results"]
            max_results = 100  # Limit the number of search results to format
            for i in range(min(len(video_results), max_results)):
                video = video_results[i]
                formatted_video = self._format_single_video(video)
                formatted_videos.append(formatted_video)
            return formatted_videos
        return None

    @retry_request()
    def search(self, query: str, channel: str = None, playlist: str = None, date_from: str = None, date_to: str = None) -> dict | None:
        """Searches the TubeArchivist API with the given query."""
        c_assert(isinstance(query, str), "query must be a string")
        if channel:
            c_assert(isinstance(channel, str), "channel must be a string")
        if playlist:
            c_assert(isinstance(playlist, str), "playlist must be a string")
        if date_from:
            c_assert(isinstance(date_from, str), "date_from must be a string")
        if date_to:
            c_assert(isinstance(date_to, str), "date_to must be a string")

        endpoint = f"{self.base_url}/api/search/"
        params = {"query": query}
        if channel:
            params["channel"] = channel
        if playlist:
            params["playlist"] = playlist
        if date_from:
            params["date_from"] = date_to
        return self._make_request(requests.get, endpoint, params=params)

    @retry_request()
    def get_user_config(self) -> dict | None:
        """Retrieves the current user's configuration."""
        endpoint = f"{self.base_url}/api/user/me/"
        return self._make_request(requests.get, endpoint)

    @retry_request()
    def update_user_config(self, data: dict) -> dict | None:
        """Updates the current user's configuration."""
        c_assert(isinstance(data, dict), "data must be a dictionary")
        endpoint = f"{self.base_url}/api/user/me/"
        return self._make_request(requests.post, endpoint, data=data)

    def test_authentication(self):
        """Tests authentication with the /api/download/process/ endpoint."""
        endpoint = f"{self.base_url}/api/download/process/"
        data = {"task_id": "test_task"}  # Dummy task ID

        # Test with Authorization header
        headers_auth = {"Authorization": f"Token {self.api_token}"}
        self._test_auth_header(endpoint, data, headers_auth)

        # Test with query parameter
        #params_auth = {"api_token": self.api_token}
        #self._test_auth_param(endpoint, data, params_auth)

    def _test_auth_header(self, endpoint, data, headers_auth):
        """Tests authentication with header."""
        try:
            headers_auth["Content-Type"] = "application/json"
            response = requests.post(endpoint, headers=headers_auth, data=json.dumps(data))
            logger.info("Authentication Test (Authorization Header):")
            logger.info(f"  Status Code: {response.status_code}")
            logger.info(f"  Content: {response.content.decode()}")
            logger.info(f"  Headers: {response.request.headers}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication Test (Authorization Header) failed: {e}")

    def _test_auth_param(self, endpoint, data, params_auth):
        """Tests authentication with parameter."""
        try:
            response = requests.post(endpoint, data=json.dumps(data), params=params_auth)
            logger.info("Authentication Test (Query Parameter):")
            logger.info(f"  Status Code: {response.status_code}")
            logger.info(f"  Content: {response.content.decode()}")
            logger.info(f"  URL: {response.url}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication Test (Query Parameter) failed: {e}")

    @retry_request()
    def get_channel_list(self) -> dict | None:
        """Retrieves a list of channels."""
        endpoint = f"{self.base_url}/api/channel/"
        return self._make_request(requests.get, endpoint)

    @retry_request()
    def get_channel(self, channel_id: str) -> dict | None:
        """Retrieves metadata for a specific channel."""
        c_assert(isinstance(channel_id, str), "channel_id must be a string")
        endpoint = f"{self.base_url}/api/channel/{channel_id}/"
        return self._make_request(requests.get, endpoint)

    @retry_request()
    def get_channel_aggs(self, channel_id: str) -> dict | None:
        """Retrieves aggregations for a specific channel."""
        c_assert(isinstance(channel_id, str), "channel_id must be a string")
        endpoint = f"{self.base_url}/api/channel/{channel_id}/aggs/"
        return self._make_request(requests.get, endpoint)

    @retry_request()
    def get_channel_nav(self, channel_id: str) -> dict | None:
        """Retrieves navigation information for a specific channel."""
        c_assert(isinstance(channel_id, str), "channel_id must be a string")
        endpoint = f"{self.base_url}/api/channel/{channel_id}/nav/"
        return self._make_request(requests.get, endpoint)

    @retry_request()
    def search_channels(self, query: str) -> dict | None:
        """Searches for channels based on a query."""
        c_assert(isinstance(query, str), "query must be a string")
        endpoint = f"{self.base_url}/api/channel/search/"
        params = {"query": query}
        return self._make_request(requests.get, endpoint, params=params)

    @retry_request()
    def get_task_list_by_name(self, task_name: str) -> dict | None:
        """Retrieves a list of tasks by name."""
        c_assert(isinstance(task_name, str), "task_name must be a string")
        endpoint = f"{self.base_url}/api/task/by-name/{task_name}/"
        return self._make_request(requests.get, endpoint)

    @retry_request()
    def get_task_details_by_id(self, task_id: str) -> dict | None:
        """Retrieves details for a specific task ID."""
        c_assert(isinstance(task_id, str), "task_id must be a string")
        endpoint = f"{self.base_url}/api/task/by-id/{task_id}/"
        return self._make_request(requests.get, endpoint)

    @retry_request()
    def get_video_comments(self, video_id: str) -> dict | None:
        """Retrieves comments for a specific video."""
        c_assert(isinstance(video_id, str), "video_id must be a string")
        endpoint = f"{self.base_url}/api/video/{video_id}/comment/"
        return self._make_request(requests.get, endpoint)

    @retry_request()
    def get_similar_videos(self, video_id: str) -> dict | None:
        """Retrieves a list of similar videos."""
        c_assert(isinstance(video_id, str), "video_id must be a string")
        endpoint = f"{self.base_url}/api/video/{video_id}/similar/"
        return self._make_request(requests.get, endpoint)


def main():
    BASE_URL = os.getenv("BASE_URL")
    API_TOKEN = os.getenv("API_TOKEN")
    logger.info("TubeArchivist API interaction script")
    logger.info(f"Base URL: {BASE_URL}")

    api = TubeArchivistAPI(BASE_URL, API_TOKEN)

    # Perform direct authentication tests
    api.test_authentication()

    # Example of initiating downloads (commented out)
    # task_id = "your_task_id"
    # handle_download_initiation(api, task_id)

    # Example of searching and displaying results
    handle_search(api)

    # Example of retrieving and displaying latest videos
    handle_latest_videos(api)

    # Example of retrieving and displaying user configuration
    handle_user_config(api)

    # Example of retrieving and displaying channel list and details
    handle_channel_info(api)

def handle_download_initiation(api: TubeArchivistAPI, task_id: str):
    """Initiates downloads for pending videos."""
    #download_result = api.trigger_pending_downloads(task_id=task_id)
    #if download_result:
    #    logger.info("\nDownload Initiation Result:")
    #    logger.info(json.dumps(download_result, indent=4))
    #else:
    #    logger.error("Failed to initiate downloads for pending videos.")
    pass

def handle_search(api: TubeArchivistAPI):
    """Searches and displays search results."""
    search_results = api.search(query="test")
    if search_results:
        logger.info("\nSearch Results:")
        formatted_search_results = api.format_search_results(search_results)
        logger.info(json.dumps(formatted_search_results, indent=4))
    else:
        logger.error("Failed to retrieve search results.")

def handle_latest_videos(api: TubeArchivistAPI):
    """Retrieves and displays latest videos."""
    latest_videos = api.get_latest_videos()
    if latest_videos:
        logger.info("\nLatest Videos:")
        formatted_videos = api.format_videos(latest_videos)
        logger.info(json.dumps(formatted_videos, indent=4))
    else:
        logger.error("Failed to retrieve latest videos.")

def handle_user_config(api: TubeArchivistAPI):
    """Retrieves and displays user configuration."""
    user_config = api.get_user_config()
    if user_config:
        logger.info("\nUser Configuration:")
        logger.info(json.dumps(user_config, indent=4))
    else:
        logger.error("Failed to retrieve user configuration.")

def handle_channel_info(api: TubeArchivistAPI):
    """Retrieves and displays channel list and details."""
    channel_list = api.get_channel_list()
    if channel_list:
        logger.info("\nChannel List:")
        logger.info(json.dumps(channel_list, indent=4))
    else:
        logger.error("Failed to retrieve channel list.")

    if channel_list and channel_list.get("data"):
        first_channel_id = channel_list["data"][0]["channel_id"]
        channel_details = api.get_channel(first_channel_id)
        if channel_details:
            logger.info(f"\nDetails for Channel ID {first_channel_id}:")
            logger.info(json.dumps(channel_details, indent=4))
        else:
            logger.error(f"Failed to retrieve details for channel ID {first_channel_id}.")

if __name__ == "__main__":
    main()
