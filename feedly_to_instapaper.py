import json
import os
import time
from datetime import datetime

from feedly_utils import get_saved_articles, get_article_url, get_article_title
from instapaper_utils import save_to_instapaper

STATE_FILE = "feedly_sync_state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"synced_ids": [], "last_run": None}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def sync():
    print(f"\n🔄 Feedly → Instapaper sync started at {datetime.now().strftime('%H:%M:%S')}")

    state = load_state()
    already_synced = set(state.get("synced_ids", []))

    since_ms = None
    if state.get("last_run"):
        last_run_dt = datetime.fromisoformat(state["last_run"])
        since_ms = int(last_run_dt.timestamp() * 1000)

    articles = get_saved_articles(since_timestamp=since_ms)

    if not articles:
        print("   No articles found in Feedly Read Later.")
        return

    new_count = 0
    failed_count = 0

    for article in articles:
        article_id = article.get("id")

        if article_id in already_synced:
            continue

        url = get_article_url(article)
        title = get_article_title("title", "Untitled")

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

        time.sleep(0.5)

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
