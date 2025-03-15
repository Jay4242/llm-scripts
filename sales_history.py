import requests
from bs4 import BeautifulSoup
import json
import re
import sys
import urllib.parse

def extract_ebay_data(url):
    """
    Fetches data from an eBay search results page and returns it as a JSON array.

    Args:
        url (str): The URL of the eBay search results page.

    Returns:
        str: A JSON array containing the extracted data.
    """

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return json.dumps([])  # Return empty JSON array in case of error

    soup = BeautifulSoup(response.content, 'html.parser')

    # Find all list items that contain the sold items
    # This selector might need adjustment based on the actual eBay page structure
    items = soup.find_all('li', class_='s-item')

    data = []
    for item in items:
        # Check for sponsored items more robustly
        if item.find('span', {'class': 's-item__sponsored-text'}):
            continue

        # Filter out "Shop on eBay" items
        image_wrapper = item.find('div', class_='s-item__image-wrapper')
        if image_wrapper and image_wrapper.find('img', alt='Shop on eBay'):
            continue
        subtitle = item.find('div', class_='s-item__subtitle')
        if subtitle and subtitle.find('span', class_='SECONDARY_INFO', string=re.compile(r'Brand New')):
            continue

        # Extract the title, handling different possible structures
        title_element = item.find('h3', class_='s-item__title')
        if title_element and title_element.text.strip() == 'Shop on eBay':
            title_element = None  # Ignore "Shop on eBay" titles
        if not title_element:
            title_element = item.find('div', class_='s-item__title')
        if title_element:
            title = title_element.text.strip()
        else:
            print("Title not found")
            continue

        # Extract the sold date
        sold_date_element = item.find('span', class_='s-item__caption--signal POSITIVE')
        if sold_date_element:
            sold_date = sold_date_element.text.replace('Sold ', '').strip()
        else:
            sold_date = 'N/A'

        # Extract the price
        price = item.find('span', class_='s-item__price')
        if price:
            price = price.text.strip()
        else:
            price = 'N/A'

        # Extract delivery price
        delivery_price = item.find('span', class_='s-item__shipping s-item__logisticsCost')
        if delivery_price:
            delivery_price = delivery_price.text.strip()
        else:
            delivery_price = 'N/A'

        data.append({
            'Item': title,
            'Sold Date': sold_date,
            'Selling Price': price,
            'Delivery Price': delivery_price
        })

    return json.dumps(data, indent=4)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        search_term = sys.argv[1]
        # URL encode the search term
        encoded_search_term = urllib.parse.quote_plus(search_term)
        ebay_url = f"https://www.ebay.com/sch/i.html?_nkw={encoded_search_term}&LH_Complete=1&LH_Sold=1"
        json_output = extract_ebay_data(ebay_url)
        print(json_output)
    else:
        print("Please provide a search term as a command-line argument.")
