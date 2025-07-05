import requests
from bs4 import BeautifulSoup

def fetch_text_from_url(url):
    try:
        page = requests.get(url)
        soup = BeautifulSoup(page.content, 'html.parser')
        return soup.get_text()
    except Exception as e:
        return f"Error fetching URL content: {e}"

