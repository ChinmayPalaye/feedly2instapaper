"""
Feedly → Instapaper Sync
------------------------
Checks your Feedly "Read Later" (Saved) list and sends any new articles
to Instapaper automatically.

SETUP:
1. Get your Feedly access token:
   - Open feedly.com in your browser and log in
   - Open browser DevTools (F12) → Application tab → Local Storage → cloud.feedly.com
   - Find the key "feedlyToken" and copy its value
   - Paste it below as FEEDLY_TOKEN

2. Get your Feedly user ID:
   - In the same DevTools Local Storage, look for "userId"
   - It looks like: "9b61e777-6ee2-476d-a158-03050694896a"
   - Paste it below as FEEDLY_USER_ID

3. Fill in your Instapaper credentials (the email/password you use to log in)

4. Install dependencies:
   pip install requests

5. Run:
   python feedly_to_instapaper.py
"""

import requests
import json
import os
import time
from datetime import datetime

# ── CONFIGURATION ──────────────────────────────────────────────────────────────

FEEDLY_TOKEN   = os.environ.get("FEEDLY_TOKEN")
FEEDLY_USER_ID = os.environ.get("FEEDLY_USER_ID")

INSTAPAPER_USERNAME = os.environ.get("IP_USERNAME")
INSTAPAPER_PASSWORD = os.environ.get("IP_PASSWORD")

# File to track which articles have already been sent
# (so we don't send duplicates on future runs)
STATE_FILE = "feedly_sync_state.json"

# ── FEEDLY ─────────────────────────────────────────────────────────────────────

FEEDLY_BASE = "https://cloud.feedly.com/v3"

def get_saved_articles(since_timestamp=None):
    """Fetch articles from Feedly's Read Later / Saved stream."""
    stream_id = f"user/{FEEDLY_USER_ID}/tag/global.saved"

    params = {
        "streamId": stream_id,
        "count": 50,
    }
    if since_timestamp:
        params["newerThan"] = since_timestamp

    headers = {
        "Authorization": f"Bearer {FEEDLY_TOKEN}"
    }

    response = requests.get(
        f"{FEEDLY_BASE}/streams/contents",
        headers=headers,
        params=params,
        timeout=15
    )

    if response.status_code == 401:
        print("❌ Feedly auth failed. Your token may have expired.")
        print("   Get a fresh one from feedly.com DevTools (see setup instructions).")
        return []

    response.raise_for_status()
    data = response.json()
    return data.get("items", [])


def extract_url(article):
    """Pull the best URL out of a Feedly article object."""
    # Try canonical URL first, then alternate
    for key in ("canonical", "alternate"):
        links = article.get(key, [])
        if links and isinstance(links, list):
            return links[0].get("href")
    # Fallback: the article's own originId is usually a URL
    origin_id = article.get("originId", "")
    if origin_id.startswith("http"):
        return origin_id
    return None


# ── INSTAPAPER ─────────────────────────────────────────────────────────────────

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


# ── STATE (tracks what's already been synced) ──────────────────────────────────

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"synced_ids": [], "last_run": None}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ── MAIN ───────────────────────────────────────────────────────────────────────

def sync():
    print(f"\n🔄 Feedly → Instapaper sync started at {datetime.now().strftime('%H:%M:%S')}")

    state = load_state()
    already_synced = set(state.get("synced_ids", []))

    since_ms = None
    if state.get("last_run"):
        last_run_dt = datetime.fromisoformat(state["last_run"])
        since_ms = int(last_run_dt.timestamp() * 1000)

    # Fetch saved articles from Feedly
    articles = get_saved_articles(since_ms)

    if not articles:
        print("   No articles found in Feedly Read Later.")
        return

    new_count = 0
    failed_count = 0

    for article in articles:
        article_id = article.get("id")

        # Skip if we've already sent this one
        if article_id in already_synced:
            continue

        url = extract_url(article)
        title = article.get("title", "Untitled")

        if not url:
            print(f"   ⚠️  Skipping article with no URL: {title}")
            continue

        print(f"   → Saving: {title[:150]}")
        success = save_to_instapaper(url, title)

        if success:
            already_synced.add(article_id)
            new_count += 1
        else:
            failed_count += 1

        # Small delay to be polite to the APIs
        time.sleep(0.5)

    # Persist state
    state["synced_ids"] = list(already_synced)
    state["last_run"] = datetime.now().isoformat()
    save_state(state)

    print(f"\n✅ Done. {new_count} new article(s) sent to Instapaper.", end="")
    if failed_count:
        print(f" {failed_count} failed.")
    else:
        print()


if __name__ == "__main__":
    sync()
