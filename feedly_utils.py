import os
import time
import requests

FEEDLY_TOKEN         = os.environ.get("FEEDLY_TOKEN")
FEEDLY_REFRESH_TOKEN = os.environ.get("FEEDLY_REFRESH_TOKEN")
FEEDLY_TOKEN_EXPIRY  = int(os.environ.get("FEEDLY_TOKEN_EXPIRY", "0"))
FEEDLY_USER_ID       = os.environ.get("FEEDLY_USER_ID")

STATE_FILE = "feedly_sync_state.json"

TOKEN_REFRESH_THRESHOLD_SECS = 7 * 24 * 60 * 60  # 1 week

FEEDLY_BASE = "https://cloud.feedly.com/v3"

# These may be updated at runtime after a token refresh
_feedly_token = FEEDLY_TOKEN
_feedly_token_expiry = FEEDLY_TOKEN_EXPIRY
def refresh_feedly_token():
    """
    Use the refresh token to get a new access token from Feedly.
    Feedly uses standard OAuth2: POST to the token endpoint with
    grant_type=refresh_token. Returns the new token on success, or
    None if the refresh fails.
    """
    global _feedly_token, _feedly_token_expiry

    print("   🔑 Feedly token expiring soon — refreshing...")

    response = requests.post(
        f"{FEEDLY_BASE}/auth/token",
        data={
            "refresh_token": FEEDLY_REFRESH_TOKEN,
            "client_id":     "feedly",
            "client_secret": "0XP4XQ07VVMDWBKUHTJM4WUQ",
            "grant_type":    "refresh_token",
        },
        timeout=15
    )

    if response.status_code != 200:
        print(f"   ❌ Token refresh failed (HTTP {response.status_code}). "
              "You may need to log into feedly.com and paste a fresh token.")
        return None

    data = response.json()
    new_token  = data.get("access_token")
    expires_in = data.get("expires_in", 0)  # seconds from now

    if not new_token:
        print("   ❌ Token refresh response had no access_token.")
        return None

    _feedly_token        = new_token
    _feedly_token_expiry = int(time.time() + expires_in) * 1000  # store as ms

    print(f"   ✅ Token refreshed. New expiry in {expires_in // 86400} days.")
    return new_token


def ensure_fresh_token():
    """Refresh the token if it will expire within TOKEN_REFRESH_THRESHOLD_SECS."""
    now_ms      = int(time.time() * 1000)
    threshold_ms = TOKEN_REFRESH_THRESHOLD_SECS * 1000

    if _feedly_token_expiry and (_feedly_token_expiry - now_ms) < threshold_ms:
        refresh_feedly_token()


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
        "Authorization": f"Bearer {_feedly_token}"
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
    for key in ("canonical", "alternate"):
        links = article.get(key, [])
        if links and isinstance(links, list):
            return links[0].get("href")
    # Fallback: the article's own originId is usually a URL
    origin_id = article.get("originId", "")
    if origin_id.startswith("http"):
        return origin_id
    return None