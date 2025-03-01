#!/usr/bin/env python3

import os
import json
import requests
from dotenv import load_dotenv
from openai import OpenAI
import httpx

load_dotenv()

class PaperlessAPI:
    def __init__(self, base_url, api_token):
        self.base_url = base_url
        self.api_token = api_token
        self.headers = {
            'Authorization': f'Token {self.api_token}',
            'Content-Type': 'application/json',
        }

    def llm(self, document, system, preprompt, postprompt, temp):
        """
        Send a document to the LLM server and return the response.
        """
        llm_base_url = os.environ.get("LLM_BASE_URL")
        client = OpenAI(base_url=llm_base_url, api_key="none", timeout=httpx.Timeout(3600))

        completion = client.chat.completions.create(
            model="llama-3.2-3b-it-q8_0",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": preprompt},
                {"role": "user", "content": document},
                {"role": "user", "content": postprompt}
            ],
            temperature=temp,
            stream=True,
        )

        response = ""
        for chunk in completion:
            if chunk.choices[0].delta.content:
                response += chunk.choices[0].delta.content

        return response

    def get(self, endpoint, params=None):
        """
        Generic GET request.
        """
        url = f"{self.base_url}/{endpoint}/"
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error during GET request: {e}")
            return None

    def post(self, endpoint, data):
        """
        Generic POST request.
        """
        url = f"{self.base_url}/{endpoint}/"
        try:
            response = requests.post(url, headers=self.headers, data=json.dumps(data))
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error during POST request: {e}")
            return None

    def patch(self, endpoint, data):
        """
        Generic PATCH request.
        """
        url = f"{self.base_url}/{endpoint}/"
        try:
            response = requests.patch(url, headers=self.headers, data=json.dumps(data))
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error during PATCH request: {e}")
            return None

    def delete(self, endpoint):
        """
        Generic DELETE request.
        """
        url = f"{self.base_url}/{endpoint}/"
        try:
            response = requests.delete(url, headers=self.headers)
            response.raise_for_status()
            return response.status_code
        except requests.exceptions.RequestException as e:
            print(f"Error during DELETE request: {e}")
            return None

    # Add specific API methods below.  Examples:
    def get_documents(self, page=1):
        """
        Retrieve a list of documents.
        """
        return self.get("documents", params={'page': page})

    def get_document(self, document_id):
        """
        Retrieve a specific document by ID.
        """
        return self.get(f"documents/{document_id}")

    def create_document(self, data):
        """
        Create a new document. Data should be a dictionary.
        """
        return self.post("documents", data)

    def search_documents(self, query, page=1):
        """
        Search for documents.
        """
        return self.get("documents", params={'query': query, 'page': page})

    def get_full_document(self, document_id):
        """
        Retrieve the full information for a specific document by ID.
        """
        return self.get(f"documents/{document_id}")


def main():
    # Load configuration from environment variables or a config file.
    base_url = os.environ.get("PAPERLESS_BASE_URL")
    api_token = os.environ.get("PAPERLESS_API_TOKEN")

    if not base_url or not api_token:
        print("Error: PAPERLESS_BASE_URL and PAPERLESS_API_TOKEN environment variables must be set.")
        return

    api = PaperlessAPI(base_url, api_token)

    # Example usage:
    documents = api.get_documents()
    if documents:
        print(f"Found {documents['count']} documents.")
        for document in documents['results']:
            print(f"  - {document['title']} (ID: {document['id']})")

    # Example of getting a specific document (replace 123 with a valid ID):
    # document = api.get_document(123)
    # if document:
    #     print(f"Document content: {document['content']}")

    # Example of searching for documents:
    query = input("Enter search query: ")
    search_results = api.search_documents(query, 1)

    if search_results and 'count' in search_results and search_results['count'] > 0:
        total_documents = search_results['count']
        page_size = len(search_results['results'])  # Assuming page_size is the number of results on the current page
        total_pages = (total_documents + page_size - 1) // page_size
        print(f"Found {total_documents} documents matching '{query}'. Total pages: {total_pages}")

        if 'results' in search_results:
            for i, document in enumerate(search_results['results']):
                print(f"  {i+1}. {document['title']} (ID: {document['id']})")

            while True:
                try:
                    selection = input(f"Enter the number of the document to view (1-{len(search_results['results'])}), or 0 to exit: ")
                    selection = int(selection)

                    if selection == 0:
                        break
                    elif 1 <= selection <= len(search_results['results']):
                        selected_document = search_results['results'][selection - 1]
                        document_id = selected_document['id']
                        full_document = api.get_full_document(document_id)
                        if full_document:
                            print(f"--- Document {document_id} ---")
                            print(f"Title: {full_document['title']}")
                            print(f"Content: {full_document['content']}")

                            # Get document details
                            document_title = full_document['title']
                            correspondent_id = full_document['correspondent']
                            correspondent = None
                            if correspondent_id:
                                correspondent = api.get(f"correspondents/{correspondent_id}")
                            correspondent_name = correspondent['name'] if correspondent else "Unknown"

                            # Get LLM prompts
                            system_prompt = "You are a helpful assistant."
                            pre_prompt = f"The following is a document titled {document_title}, from {correspondent_name}:"
                            post_prompt = "Summarize the document in three sentences or less."
                            temperature = 0.7

                            # Call the LLM function
                            llm_response = api.llm(full_document['content'], system_prompt, pre_prompt, post_prompt, temperature)
                            print(f"Summary: {llm_response}")

                            return  # Exit after displaying the document and summary
                        else:
                            print(f"Failed to retrieve document {document_id}.")
                    else:
                        print("Invalid selection. Please try again.")
                except ValueError:
                    print("Invalid input. Please enter a number.")
    else:
        print(f"No documents found matching '{query}'.")


if __name__ == "__main__":
    main()
