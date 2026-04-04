import os
import requests

INSTAPAPER_USERNAME  = os.environ.get("INSTAPAPER_USERNAME")
INSTAPAPER_PASSWORD  = os.environ.get("INSTAPAPER_PASSWORD")

INSTAPAPER_ADD_URL = "https://www.instapaper.com/api/add"

def save_to_instapaper(url, title=None):
    """Save a URL to Instapaper using their simple API."""
    params = {
        "username": INSTAPAPER_USERNAME,
        "password": INSTAPAPER_PASSWORD,
        "url": url,
    }
    if title:
        params["title"] = title

    response = requests.post(INSTAPAPER_ADD_URL, data=params, timeout=15)

    if response.status_code == 201:
        return True
    elif response.status_code == 403:
        print("❌ Instapaper auth failed. Check your username and password.")
        return False
    else:
        print(f"⚠️  Instapaper returned unexpected status {response.status_code} for: {url}")
        return False
