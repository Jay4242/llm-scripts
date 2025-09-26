#!/usr/bin/env python3
"""
Simple RSS fetcher and parser for the CBS News Technology feed.

This script downloads the RSS XML from the given URL, parses the
channel and its items, and prints a short summary of each article.
"""

import urllib.request
import xml.etree.ElementTree as ET
import json
import logging
import re
import signal
import sys
from bs4 import BeautifulSoup
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
# Set httpx logging to WARNING level to suppress INFO level logs
logging.getLogger("httpx").setLevel(logging.WARNING)
import httpx
import argparse
import random
import subprocess
import pyttsx3
engine = pyttsx3.init()
from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()
backend_host = os.getenv("LLM_BACKEND_HOST", "localhost")
backend_port = os.getenv("LLM_BACKEND_PORT", "8000")
from typing import List, Dict

logger = logging.getLogger(__name__)

# Global flag to track shutdown request
shutdown_requested = False


def fetch_cbs_rss(url: str) -> bytes:
    """
    Retrieve the raw RSS XML from the specified URL.

    Args:
        url: The RSS feed URL.

    Returns:
        The raw bytes of the RSS XML.
    """
    with urllib.request.urlopen(url) as response:
        return response.read()


def parse_cbs_rss(xml_data: bytes) -> List[Dict[str, str | None]]:
    """
    Parse the RSS XML and extract article information.

    Args:
        xml_data: Raw bytes of the RSS XML.

    Returns:
        A list of dictionaries, each containing title, link,
        description, and pubDate for an article.
    """
    root = ET.fromstring(xml_data)
    channel = root.find("channel")
    if channel is None:
        raise ValueError("No <channel> element found in RSS feed")

    items: List[Dict[str, str | None]] = []
    for item in channel.findall("item"):
        title = item.findtext("title", default="No title")
        link = item.findtext("link", default="No link")
        description = item.findtext("description", default="No description")
        pub_date = item.findtext("pubDate", default="No publication date")
        # Extract image URL if available
        image_url = None
        # Fallback: look for a plain <image> tag containing the URL
        if image_url is None:
            image_text = item.findtext("image")
            if image_text:
                image_url = image_text
        items.append(
            {
                "title": title,
                "link": link,
                "description": description,
                "pubDate": pub_date,
                "image_url": image_url,
            }
        )
    return items

def format_cbs_articles_for_llm(articles: List[Dict[str, str | None]]) -> str:
    """Return a JSON string of articles suitable for LLM consumption."""
    # Filter out image_url from each article
    articles_filtered = [
        {k: v for k, v in article.items() if k != "image_url"}
        for article in articles
    ]
    return json.dumps(articles_filtered, ensure_ascii=False, indent=2)


def send_to_llm(
    system: str,
    preprompt: str,
    prompt: str,
    postprompt: str,
    temp: float = 0.6,
) -> str:
    """
    Send a multi‑part prompt to the LLM backend and return the streamed response.

    Parameters
    ----------
    system : str
        The system message content.
    preprompt : str
        The first user message (e.g., a description or context).
    prompt : str
        The second user message containing the main content (e.g., cleaned RSS data).
    postprompt : str
        The third user message (e.g., a command or question).
    temp : float, optional
        Temperature for the model, by default 0.7.

    Returns
    -------
    str
        The concatenated content of the streamed response.
    """
    client = OpenAI(
        base_url=f"http://{backend_host}:{backend_port}/v1",
        api_key="none",
        timeout=httpx.Timeout(7200),
    )

    logger.debug(f"Sending request to LLM with system: {system}")
    completion = client.chat.completions.create(
        model="Qwen3-30B-A3B-Instruct-2507-Q8_0",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": preprompt},
            {"role": "user", "content": prompt},
            {"role": "user", "content": postprompt},
        ],
        temperature=temp,
        stream=True,
    )

    result = ""
    for chunk in completion:
        if chunk.choices and chunk.choices[0].delta.content:
            result += chunk.choices[0].delta.content
    return result


def fetch_article_content(url: str) -> Dict[str, str]:
    """
    Fetch and clean the content of an article using BeautifulSoup.

    Args:
        url: The URL of the article to fetch.

    Returns:
        A dictionary containing title, body, and other relevant information.
    """
    try:
        response = httpx.get(url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title
        title = ""
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text().strip()
        
        # Extract main content - try common selectors
        content = ""
        # Try to find article content
        article = soup.find('article')
        if article:
            content = article.get_text(strip=True)
        else:
            # Try common content containers
            content_selectors = ['div.article-body', 'div.story-content', 'div.post-content', 'div.entry-content']
            for selector in content_selectors:
                element = soup.select_one(selector)
                if element:
                    content = element.get_text(strip=True)
                    break
            
            # If no specific content found, get all text from body
            if not content:
                body = soup.find('body')
                if body:
                    content = body.get_text(strip=True)
        
        # Clean up the content
        content = re.sub(r'\s+', ' ', content).strip()
        
        return {
            "title": title,
            "url": url,
            "content": content[:5000]  # Limit content length
        }
    except Exception as e:
        logger.error(f"Error fetching article content from {url}: {e}")
        return {
            "title": "Error",
            "url": url,
            "content": f"Failed to fetch content: {str(e)}"
        }


def signal_handler(sig, frame):
    global shutdown_requested
    if shutdown_requested:
        print("\nSecond Ctrl-C received. Exiting immediately.")
        sys.exit(0)
    else:
        print("\nCtrl-C pressed. Will exit after current article.")
        shutdown_requested = True

def speak(text: str) -> None:
    global engine
    engine.say(text)
    engine.runAndWait()

def main() -> None:
    """
    Main entry point: fetch the feed, parse it, and print a summary.
    """
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)

    parser = argparse.ArgumentParser(description="Fetch and process CBS News RSS feed.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--speak", action="store_true", help="Speak the summary using pyttsx3")
    parser.add_argument("--save", action="store_true", help="Save processed URLs to llm-rss-output.txt and skip them next run")
    parser.add_argument("--random", action="store_true", help="Select a random article instead of using the LLM")
    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    feed_url = "https://www.cbsnews.com/latest/rss/technology"
    try:
        raw_xml = fetch_cbs_rss(feed_url)
    except Exception as exc:
        print(f"Error fetching RSS feed: {exc}")
        return

    try:
        articles: List[Dict[str, str | None]] = parse_cbs_rss(raw_xml)
    except Exception as exc:
        print(f"Error parsing RSS feed: {exc}")
        return

    if not articles:
        print("No articles found in the feed.")
        return

    # Load previously processed URLs if --save flag is used
    saved_urls = set()
    if args.save and os.path.exists("llm-rss-output.txt"):
        with open("llm-rss-output.txt", "r", encoding="utf-8") as f:
            for line in f:
                saved_urls.add(line.strip())
    # Exclude already processed URLs when --save is used
    if args.save:
        articles = [a for a in articles if a.get("link") not in saved_urls]

    # Process articles in a loop, letting the LLM pick one each time
    while articles and not shutdown_requested:
        if args.random:
            article = random.choice(articles)
            url = article.get("link")
            print(f"Randomly selected URL: {url}")
            logger.debug(f"Randomly selected URL: {url}")
        else:
            formatted = format_cbs_articles_for_llm(articles)
            logger.debug(f"Formatted articles: {formatted}")
            system = "You're an expert news analyst."
            preprompt = "You are given a list of recent articles in JSON format. Examine them and select the most important one. Do not construct the URL from the title; use the 'link' field exactly as provided. Respond with the exact URL from that field, and nothing else."
            prompt = formatted
            postprompt = "Select the article you think is most important. Return only the URL from the 'link' field of that article, exactly as it appears, with no additional text, no explanations, no formatting."
            result = send_to_llm(system, preprompt, prompt, postprompt)
            result = re.sub(r'<think>.*?</think>', '', result, flags=re.DOTALL)
            url_match = re.search(r'https?://[^\s"\']+', result)
            if not url_match:
                logger.warning("No URL found in LLM response.")
                break
            url = url_match.group(0)
            # Ensure the URL is one of the article links
            if url not in [a.get("link") for a in articles]:
                logger.warning(f"URL {url} not found in article list; skipping.")
                continue
            if args.save and url in saved_urls:
                logger.info(f"Skipping already processed URL: {url}")
                # Remove from list to avoid re‑processing
                articles = [a for a in articles if a.get("link") != url]
                continue
            print(f"Selected URL: {url}")
            logger.debug(f"Selected URL: {url}")

        # Fetch the article content
        article_data = fetch_article_content(url)

        # Send article information to LLM for summarization
        system = "You're an expert news analyst."
        preprompt = "Analyze the following article and provide a summary."
        prompt = f"Title: {article_data['title']}\nURL: {article_data['url']}\nContent: {article_data['content']}"
        postprompt = "Provide a concise summary of the article's main points. Do not include any preamble or further explanation - just the summary."
        result = send_to_llm(system, preprompt, prompt, postprompt)
        result = re.sub(r'<think>.*?</think>', '', result, flags=re.DOTALL)
        # Filter out blank lines and ensure one blank line between stories
        lines = [line for line in result.splitlines() if line.strip()]
        if lines:
            summary_text = "\n".join(lines)
            print(summary_text)
            if args.speak:
                speak(summary_text)
        print()

        # Save the URL if requested
        if args.save:
            with open("llm-rss-output.txt", "a", encoding="utf-8") as f:
                f.write(url + "\n")
        # Remove the processed article from the list
        articles = [a for a in articles if a.get("link") != url]

        if shutdown_requested:
            print("Shutting down after current article...")
            break

    print("Done.")


if __name__ == "__main__":
    main()
