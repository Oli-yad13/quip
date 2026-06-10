"""Shared logic used by both the interactive session (tui.py) and the plain CLI (main.py)."""

import json
import os
import subprocess
from pathlib import Path

HERE = Path(__file__).parent
DRAFTS_DIR = HERE / "drafts"
CONFIG_FILES = ["voice.md", "topics.md", "categories.md"]
EDIT_ALIASES = {
    "voice": "voice.md", "topics": "topics.md", "categories": "categories.md",
    "sources": "xscrape.py", "env": ".env",
}


def draft_files(status: str | None = None) -> list[Path]:
    if not DRAFTS_DIR.exists():
        return []
    files = sorted(DRAFTS_DIR.glob("*.json"))
    if status is None:
        return files
    return [f for f in files if json.loads(f.read_text(encoding="utf-8"))["status"] == status]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, record: dict) -> None:
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")


def copy_to_clipboard(text: str) -> bool:
    """Copy text to the Windows clipboard. Returns True on success."""
    try:
        subprocess.run("clip", input=text, text=True, encoding="utf-8", check=True)
        return True
    except Exception:
        return False


def init_config() -> list[str]:
    """Seed editable config + .env from templates (never overwrites). Returns names made."""
    made = []
    for name in CONFIG_FILES:
        real, example = HERE / name, HERE / name.replace(".md", ".example.md")
        if not real.exists() and example.exists():
            real.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
            made.append(name)
    env, env_ex = HERE / ".env", HERE / ".env.example"
    if not env.exists() and env_ex.exists():
        env.write_text(env_ex.read_text(encoding="utf-8"), encoding="utf-8")
        made.append(".env")
    return made


def edit_config(name: str) -> str | None:
    """Open a config file in the default editor. Returns an error message, or None on success."""
    target = HERE / EDIT_ALIASES.get(name, name)
    if not target.exists():
        return f"{target.name} doesn't exist yet — run init first."
    try:
        os.startfile(target)  # Windows: opens in the default editor
    except Exception:
        subprocess.run(["notepad", str(target)])
    return None


def _reload_env() -> None:
    """Pick up .env edits (e.g. a freshly pasted cookie) without restarting quip."""
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
    except Exception:
        pass


def scrape_and_generate(count: int) -> tuple[list[dict], int, bool]:
    """Scrape X (with HN/dev.to fallback) and draft posts. Returns (drafts, n_sources, used_fallback)."""
    _reload_env()
    from xscrape import scrape_x
    from generate import generate_drafts

    trending = scrape_x()
    used_fallback = False
    if not trending:
        from sources import fetch_all
        trending = fetch_all()
        used_fallback = True
    drafts = generate_drafts(trending, count)
    return drafts, len(trending), used_fallback


def topic_and_generate(topic: str, count: int) -> tuple[list[dict], int]:
    """Search X for a specific topic you typed and draft posts about it. Returns (drafts, n_found)."""
    _reload_env()
    from xscrape import scrape_topic
    from generate import generate_drafts

    found = scrape_topic(topic)
    items = found or [{"source": "topic", "title": topic, "url": "", "points": 0}]
    drafts = generate_drafts(items, count, focus=topic)
    return drafts, len(found)
