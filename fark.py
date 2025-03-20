import requests
from bs4 import BeautifulSoup
import argparse
import random

def fetch_fark_headlines():
    url = "https://www.fark.com/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
    return response.content

def parse_fark_headlines(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    headlines = []
    headline_container = soup.find(id="headline_container")
    if headline_container:
        for td in headline_container.find_all("td", class_="headlineSourceImage"):
            a_tag = td.find("a", class_="outbound_link")
            if a_tag:
                url = a_tag["href"]
                # Find the parent table row
                parent_tr = td.find_parent("tr")
                # Find the headlineText td within the same row
                headline_text_td = parent_tr.find("td", class_="headlineText")
                if headline_text_td:
                    headline_span = headline_text_td.find("span", class_="headline")
                    if headline_span:
                        headline_a = headline_span.find("a", class_="outbound_link")
                        if headline_a:
                            tag = headline_a.text.strip()
                            if "photoshop" not in tag.lower() and "youtube" not in tag.lower():
                                headlines.append({"url": url, "tag": tag})
    return headlines

def resolve_redirect_url(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        refresh_tag = soup.find("meta", attrs={"http-equiv": "refresh"})
        if refresh_tag:
            content = refresh_tag["content"]
            redirect_url = content.split("url=")[-1]
            return redirect_url
        else:
            a_tag = soup.find("a")
            if a_tag:
                redirect_url = a_tag["href"]
                return redirect_url
            else:
                return url  # If no meta refresh tag or a tag is found, return the original URL
    except requests.exceptions.RequestException as e:
        print(f"Error resolving URL {url}: {e}")
        return url  # Return the original URL on error

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Fetch and parse Fark headlines.")
    parser.add_argument("--shuffle", action="store_true", help="Shuffle the output.")
    parser.add_argument("--resolve", help="Resolve the redirect URL.")
    args = parser.parse_args()

    if args.resolve:
        resolved_url = resolve_redirect_url(args.resolve)
        print(resolved_url)
    else:
        html_content = fetch_fark_headlines()
        headlines = parse_fark_headlines(html_content)

        if args.shuffle:
            random.shuffle(headlines)

        for headline in headlines:
            url = headline['url']
            print(f"{url} | {headline['tag']}")
