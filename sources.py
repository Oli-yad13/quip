"""Fetch trending dev content from free, legal sources (no X scraping needed)."""

import requests

HN_TOP = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM = "https://hacker-news.firebaseio.com/v0/item/{}.json"
DEVTO = "https://dev.to/api/articles?top=1&per_page=10"


def hackernews(limit: int = 10) -> list[dict]:
    ids = requests.get(HN_TOP, timeout=15).json()[:limit]
    items = []
    for i in ids:
        item = requests.get(HN_ITEM.format(i), timeout=15).json()
        if item and item.get("type") == "story":
            items.append({
                "source": "hackernews",
                "title": item.get("title", ""),
                "url": item.get("url", f"https://news.ycombinator.com/item?id={i}"),
                "points": item.get("score", 0),
            })
    return items


def devto(limit: int = 10) -> list[dict]:
    articles = requests.get(DEVTO, timeout=15).json()[:limit]
    return [{
        "source": "dev.to",
        "title": a["title"],
        "url": a["url"],
        "points": a.get("positive_reactions_count", 0),
    } for a in articles]


def fetch_all() -> list[dict]:
    items = []
    for fn in (hackernews, devto):
        try:
            items.extend(fn())
        except Exception as e:
            print(f"  warning: {fn.__name__} failed ({e})")
    return items
