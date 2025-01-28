import requests
import xml.etree.ElementTree as ET

# Configuration
API_KEY = "d5b581ea8f60482e88c30a34d1c6064e"  # Replace with your IndexNow API key
WEBSITE_HOST = "thinhdanggroup.github.io"  # Replace with your website domain
KEY_LOCATION = f"https://{WEBSITE_HOST}/{API_KEY}.txt"  # URL to your key file
INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"
SITEMAP_URL = "https://thinhdanggroup.github.io/c-sitemap.xml"  # Your sitemap URL

def fetch_sitemap_urls(sitemap_url):
    """
    Fetches and parses the sitemap to extract URLs.
    """
    try:
        response = requests.get(sitemap_url)
        response.raise_for_status()  # Raise an error for bad status codes

        # Parse the XML content
        root = ET.fromstring(response.content)
        namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = [loc.text for loc in root.findall(".//ns:loc", namespace)]

        print(f"Fetched {len(urls)} URLs from sitemap.")
        return urls
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch sitemap: {e}")
        return []

def submit_to_indexnow(urls):
    """
    Submits a list of URLs to IndexNow.
    """
    payload = {
        "host": WEBSITE_HOST,
        "key": API_KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": urls
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(INDEXNOW_ENDPOINT, json=payload, headers=headers)
        response.raise_for_status()  # Raise an error for bad status codes
        print(f"Successfully submitted {len(urls)} URLs to IndexNow.")
        print(f"Response: {response.status_code}, {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to submit URLs: {e}")

if __name__ == "__main__":
    # Step 1: Fetch URLs from the sitemap
    urls = fetch_sitemap_urls(SITEMAP_URL)

    if urls:
        # Step 2: Submit URLs to IndexNow
        submit_to_indexnow(urls)
    else:
        print("No URLs found in the sitemap.")