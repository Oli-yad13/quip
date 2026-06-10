"""Scrape X (Twitter) for trending dev content using Scrapling.

Flow: run `login` once — a visible browser opens, you sign into X, and the session
is saved to a local profile (./xprofile). After that, scraping runs headless using
that saved login. No Chrome remote-debugging, no CDP — just one persistent profile.

Heads up: scraping X is against its Terms of Service. Use a throwaway account,
keep volume low, and expect the CSS selectors to need fixing when X changes its UI.
"""

import os
import random
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote

from scrapling.fetchers import StealthySession

HERE = Path(__file__).parent
PROFILE_DIR = str(HERE / "xprofile")  # persistent browser profile (holds your X login)
LOGGED_IN_SELECTOR = '[data-testid="SideNav_AccountSwitcher_Button"]'


def _x_cookies():
    """Auth via the auth_token cookie from your normal browser — avoids automated login.

    The most reliable way to authenticate: log into X in your everyday browser, copy
    the `auth_token` cookie, and put it in .env as X_AUTH_TOKEN. No passkey, no typing
    into a controlled window, no automation detection.
    """
    token = os.environ.get("X_AUTH_TOKEN")
    if not token:
        return None
    cookies = [{"name": "auth_token", "value": token, "domain": ".x.com", "path": "/"}]
    ct0 = os.environ.get("X_CT0")
    if ct0:
        cookies.append({"name": "ct0", "value": ct0, "domain": ".x.com", "path": "/"})
    return cookies

# ── Sources ───────────────────────────────────────────────────────────────
# Big pool of dev voices + topic searches. Each run randomly samples a few
# (SAMPLE_PER_RUN) so you get variety day-to-day without scraping all of them
# every time (which would be slow and raise the ban risk). Add/remove freely.

# Dev accounts worth reacting to / learning from.
ACCOUNTS = [
    "t3dotgg",        # Theo
    "ThePrimeagen",
    "dan_abramov2",   # Dan Abramov
    "kentcdodds",
    "swyx",
    "rauchg",         # Vercel CEO
    "leeerob",        # Lee Robinson
    "cassidoo",
    "wesbos",
    "mxstbr",         # Max Stoiberg
    "adamwathan",     # Tailwind
    "youyuxi",        # Evan You (Vue/Vite)
    "GergelyOrosz",   # Pragmatic Engineer
    "simonw",         # Simon Willison (LLMs)
    "karpathy",
    "mitchellh",      # HashiCorp / Ghostty
    "shadcn",
    "levelsio",       # indie hacker
    "marc_louvion",   # indie hacker
    "steventey",
]

# Topic searches. `min_faves:` keeps only posts with real traction;
# `-filter:replies lang:en` keeps it to original English posts.
TOPICS = [
    "MCP (AI OR agents) min_faves:200 -filter:replies lang:en",  # histori's wheelhouse
    "Claude Code min_faves:200 -filter:replies lang:en",
    "local-first min_faves:150 -filter:replies lang:en",
    "AI coding agents min_faves:300 -filter:replies lang:en",
    "typescript min_faves:400 -filter:replies lang:en",
    "react min_faves:500 -filter:replies lang:en",
    "webdev min_faves:500 -filter:replies lang:en",
    "self-hosting min_faves:200 -filter:replies lang:en",
    "build in public min_faves:200 -filter:replies lang:en",
    "open source min_faves:500 -filter:replies lang:en",
    "SQLite min_faves:200 -filter:replies lang:en",
    "developer experience min_faves:200 -filter:replies lang:en",
]

# Full pool, and how many to scrape per run.
QUERIES = [f"from:{a}" for a in ACCOUNTS] + TOPICS
SAMPLE_PER_RUN = 7

# Also pull from your own home/following timeline (people you actually follow).
INCLUDE_FOLLOWING = True


def login() -> None:
    """Open a visible browser so you can sign into X once. Saves the session to ./xprofile."""
    print("Opening X in a browser window...")
    print("Sign in there. The moment you reach your home feed, quip saves it and closes.")
    print("(Take your time — it waits up to 5 minutes.)")

    def _wait_until_logged_in(page):
        try:
            page.wait_for_selector(LOGGED_IN_SELECTOR, timeout=300000)  # 5 min
        except Exception:
            pass

    try:
        with StealthySession(headless=False, user_data_dir=PROFILE_DIR) as session:
            session.fetch("https://x.com/login", page_action=_wait_until_logged_in, timeout=320000)
    except Exception as exc:
        print(f"  login window closed early ({exc}). If you finished signing in, you're fine.")
        return
    print("Saved. Now run:  draft 3   or   about <topic>")


@contextmanager
def _session_ctx():
    """Headless scraping session. Prefers the auth_token cookie; falls back to the saved profile."""
    cookies = _x_cookies()
    if cookies:
        session = StealthySession(headless=True, cookies=cookies)
    else:
        session = StealthySession(headless=True, user_data_dir=PROFILE_DIR)
    session.__enter__()
    try:
        yield session
    finally:
        try:
            session.__exit__(None, None, None)
        except Exception:
            pass


def _scroll(page) -> None:
    """Scroll to load more tweets into the DOM after the page settles."""
    for _ in range(3):
        page.mouse.wheel(0, 3000)
        page.wait_for_timeout(1500)


def _logged_in(session) -> bool:
    """Check the saved profile is signed into X before burning time on queries."""
    try:
        page = session.fetch("https://x.com/home", network_idle=True, timeout=30000)
    except Exception:
        return False
    # These elements only render for a signed-in user.
    return bool(
        page.css(LOGGED_IN_SELECTOR)
        or page.css('[data-testid="primaryColumn"] article')
    )


def _scrape_home(session, limit: int = 15) -> list[dict]:
    """Scrape your home/following timeline — posts from people you actually follow."""
    try:
        page = session.fetch(
            "https://x.com/home",
            wait_selector='article[data-testid="tweet"]',
            network_idle=True,
            page_action=_scroll,
            timeout=30000,
        )
    except Exception:
        return []
    items = _extract(page)
    for it in items:
        it["source"] = "x-following"
    return items[:limit]


def _extract(page) -> list[dict]:
    items = []
    for art in page.css('article[data-testid="tweet"]'):
        text = " ".join(art.css('div[data-testid="tweetText"] ::text').getall()).strip()
        if not text:
            continue
        link = art.css('a[href*="/status/"]::attr(href)').get()
        url = f"https://x.com{link}" if link else ""
        items.append({"source": "x", "title": text, "url": url, "points": 0})
    return items


def scrape_topic(topic: str, per: int = 12) -> list[dict]:
    """Search X for a specific topic you typed (e.g. 'Fable 5'). Pulls latest + top posts."""
    seen, results = set(), []
    with _session_ctx() as session:
        if not _logged_in(session):
            print("  Not authenticated with X. Easiest fix: put your auth_token cookie")
            print("  in .env as X_AUTH_TOKEN (see .env.example). Or run  login.")
            return []
        for mode in ("live", "top"):  # latest, then the highest-engagement posts
            url = f"https://x.com/search?q={quote(topic)}&f={mode}"
            try:
                page = session.fetch(
                    url,
                    wait_selector='article[data-testid="tweet"]',
                    network_idle=True,
                    page_action=_scroll,
                    timeout=30000,
                )
            except Exception:
                continue
            for item in _extract(page)[:per]:
                if item["title"] not in seen:
                    seen.add(item["title"])
                    results.append(item)
    return results


def scrape_x(queries: list[str] | None = None, per_query: int = 5) -> list[dict]:
    """Fetch latest tweets for a sample of search queries. Returns sources-compatible dicts."""
    if queries is None:
        queries = random.sample(QUERIES, min(SAMPLE_PER_RUN, len(QUERIES)))
    seen, results = set(), []
    print(f"  sampling {len(queries)} of {len(QUERIES)} sources this run.")

    with _session_ctx() as session:
        if not _logged_in(session):
            print("  Not authenticated with X. Easiest fix: put your auth_token cookie")
            print("  in .env as X_AUTH_TOKEN (see .env.example). Or run  login.")
            return []  # caller falls back to Hacker News / dev.to

        if INCLUDE_FOLLOWING:
            print("  reading your home/following feed...")
            for item in _scrape_home(session):
                if item["title"] not in seen:
                    seen.add(item["title"])
                    results.append(item)

        for q in queries:
            url = f"https://x.com/search?q={q.replace(' ', '%20')}&f=live"
            try:
                page = session.fetch(
                    url,
                    wait_selector='article[data-testid="tweet"]',
                    network_idle=True,
                    page_action=_scroll,
                    timeout=30000,
                )
            except Exception:
                print(f"  warning: no results for {q!r} (skipping)")
                continue

            for item in _extract(page)[:per_query]:
                if item["title"] not in seen:
                    seen.add(item["title"])
                    results.append(item)

    return results
