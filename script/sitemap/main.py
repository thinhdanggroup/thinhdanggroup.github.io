import requests
import xml.etree.ElementTree as ET

# Configuration
WEBSITE_HOST = "thinhdanggroup.github.io"  # Replace with your website domain
SITEMAP_URL = "https://thinhdanggroup.github.io/c-sitemap.xml"  # Your sitemap URL
ROBOTS_TXT_PATH = "robots.txt"  # Path to save the robots.txt file


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


def generate_robots_txt(sitemap_url, robots_txt_path):
    """
    Generates or updates the robots.txt file with the sitemap URL.
    """
    robots_txt_content = f"""# robots.txt for {WEBSITE_HOST}
User-agent: *
Allow: /

Sitemap: {sitemap_url}
"""

    try:
        with open(robots_txt_path, "w") as robots_file:
            robots_file.write(robots_txt_content)
        print(f"Successfully generated/updated {robots_txt_path}.")
    except Exception as e:
        print(f"Failed to generate/update {robots_txt_path}: {e}")


if __name__ == "__main__":
    # Step 1: Generate/update robots.txt
    generate_robots_txt(SITEMAP_URL, ROBOTS_TXT_PATH)
