"""Draft posts with GitHub Models (free with your GitHub account — no credit card).

Uses the OpenAI-compatible endpoint at https://models.github.ai/inference,
authenticated with a GitHub personal access token. Free rate limits easily
cover a few drafting calls per day.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

from openai import OpenAI

DRAFTS_DIR = Path(__file__).parent / "drafts"

# Provider is OpenAI-compatible and swappable via .env, so you're not locked to GitHub.
# Default = GitHub Models (free with any GitHub account). To use another provider,
# set AI_BASE_URL + AI_API_KEY + MODEL (see .env.example for Ollama/Groq/OpenAI/etc.).
BASE_URL = os.environ.get("AI_BASE_URL", "https://models.github.ai/inference")
API_KEY = os.environ.get("AI_API_KEY") or os.environ.get("GITHUB_TOKEN")
MODEL = os.environ.get("MODEL", "openai/gpt-5-chat")


def _read(name: str) -> str:
    """Read a config file; fall back to its .example template if the user hasn't made one."""
    base = Path(__file__).parent
    real = base / name
    if real.exists():
        return real.read_text(encoding="utf-8")
    example = base / name.replace(".md", ".example.md")
    return example.read_text(encoding="utf-8") if example.exists() else ""


def _parse_json(raw: str) -> dict:
    # strip ```json fences if the model adds them
    raw = re.sub(r"^```(json)?\s*|\s*```$", "", raw.strip())
    return json.loads(raw)


def _humanize(text: str) -> str:
    """Strip the AI tells that survive the prompt — mainly em/en-dash sandwiches."""
    text = text.replace("—", ", ").replace("–", "-")
    text = re.sub(r"\s+([,.])", r"\1", text)   # no space before , or .
    text = re.sub(r",\s*,", ",", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def _recent_drafts(limit: int = 15) -> list[str]:
    """The last few drafts, so we can tell the model NOT to repeat itself across runs."""
    if not DRAFTS_DIR.exists():
        return []
    out = []
    for f in sorted(DRAFTS_DIR.glob("*.json"))[-limit:]:
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")).get("text", ""))
        except Exception:
            pass
    return [t for t in out if t]


SPECIFICITY_RULES = (
    "QUALITY BAR — most important rules:\n"
    "- Be SPECIFIC and CONCRETE. Name the actual thing: the tool, version, person, "
    "number, or claim from the feed. A post that could have been written a year ago, "
    "or about any tool, is a FAILURE — rewrite it.\n"
    "- Take a real, falsifiable stance. Say something a reasonable dev could disagree with.\n"
    "- No vague filler ('AI is changing everything', 'exciting times', 'the future is here', "
    "'developers should pay attention'). Ban these.\n"
    "- React to what is ACTUALLY in the feed below — quote the detail, the version, the drama.\n"
    "- Sound like a human with an opinion, not a newsletter summary.\n"
    "Example of BAD (vague): 'New AI models are pushing the boundaries of what's possible.'\n"
    "Example of GOOD (specific): 'Fable 5 doing 1M context at the same price as Opus is the "
    "actual headline. nobody's pricing long-context like this yet.'\n"
)

HUMAN_VOICE_RULES = (
    "SOUND HUMAN — this is the hardest and most important part. Real bangers are "
    "SHORT, blunt, and reactive. Match the rhythm of the example posts in the voice "
    "guide above all else.\n"
    "- BE SHORT. Most posts under 150 characters; a great one can be under 100. "
    "Do NOT pad to fill 270. If you can cut a word, cut it.\n"
    "- Say the thing and STOP. No tidy conclusion, no 'and that's gonna change X', "
    "no moral, no explaining the implication. The reaction IS the post.\n"
    "- Be blunt and take a hard stance. Spicy and a little rude is good. No 'on the "
    "other hand', no hedging, no balance.\n"
    "- Raw reactions are great: 'holy shit', 'this is wild', 'nobody asked for this'.\n"
    "- No em-dash sandwiches, no 'it's not just X, it's Y', no rule-of-three "
    "('faster, cleaner, smarter'), no 'Here's the thing' / 'Let's be honest' openers.\n"
    "- Lowercase-leaning, fragments fine. Type like a dev firing off a thought, not a "
    "brand account or LinkedIn post. Vary every opening.\n"
)


def generate_drafts(trending: list[dict], count: int = 3, focus: str | None = None) -> list[dict]:
    if not API_KEY:
        raise SystemExit(
            "\nNo API key set.\n"
            "  Easiest (free): put a GitHub token in .env as  GITHUB_TOKEN=github_pat_...\n"
            "  Get one at https://github.com/settings/tokens (fine-grained, Models: read).\n"
            "  Or use another provider by setting AI_BASE_URL + AI_API_KEY in .env.\n"
        )
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

    news = "\n".join(
        f"- [{t['source']}, {t['points']} points] {t['title']} ({t['url']})"
        for t in trending
    )

    if focus:
        variety = (
            f"EVERY post must be specifically about: {focus}. Pull concrete details "
            f"from the feed items below about it. Vary the angle (a take, a question, "
            f"a reaction, a tie-in to my own work) but stay on this topic."
        )
        user_intro = f"What people are saying about '{focus}' right now:"
    else:
        variety = (
            "Spread the posts across DIFFERENT categories so the set has variety. "
            "Mostly react to the feed below. You may mention my own work in AT MOST ONE "
            "post — and if you do, ROTATE which project (don't default to the same one "
            "every time) and don't lean on the same hook (local-first, my country's "
            "internet) you've used before. Each post must cover a different subject."
        )
        user_intro = "Recent posts from my feed and dev community:"

    recent = _recent_drafts()
    avoid = ""
    if recent:
        joined = "\n".join(f"- {t}" for t in recent[-10:])
        avoid = (
            "\n\nDO NOT REPEAT THESE — you drafted them recently. Pick different "
            f"subjects, angles, and projects:\n{joined}\n"
        )

    try:
        response = _create(client, count, news, focus, variety, user_intro, avoid)
    except Exception as e:
        msg = str(e)
        if "429" in msg or "Too many requests" in msg or "rate limit" in msg.lower():
            raise SystemExit(
                f"\nHit the GitHub Models rate limit. The current model ({MODEL}) has a "
                "low free daily quota.\n"
                "  - Wait a while (the limit resets), or\n"
                "  - Set  MODEL=openai/gpt-4o-mini  in .env for a much higher free quota,\n"
                "    then run again.\n"
            )
        raise

    drafts = _parse_json(response.choices[0].message.content)["drafts"]

    DRAFTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    saved = []
    for i, d in enumerate(drafts):
        record = {
            "text": _humanize(d["text"]),
            "category": d.get("category", ""),
            "inspiration": d.get("inspiration", ""),
            "status": "pending",  # pending -> posted (or skipped)
            "created": stamp,
        }
        path = DRAFTS_DIR / f"{stamp}_{i}.json"
        path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        saved.append(record)
    return saved


def _create(client, count, news, focus, variety, user_intro, avoid):
    return client.chat.completions.create(
        model=MODEL,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You draft X (Twitter) posts for a developer. Follow the voice "
                    "guide exactly. Each post must stand alone and be under 270 "
                    f"characters.\n\n{SPECIFICITY_RULES}\n{HUMAN_VOICE_RULES}\n{variety}\n\n"
                    'Return ONLY JSON in this exact shape: {"drafts": [{"text": '
                    '"the post", "category": "one category name", "inspiration": '
                    '"the specific thing this reacts to"}]}\n\n'
                    f"== VOICE GUIDE ==\n{_read('voice.md')}\n\n"
                    f"== CATEGORIES ==\n{_read('categories.md')}\n\n"
                    f"== MY TOPICS ==\n{_read('topics.md')}"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"{user_intro}\n{news}\n{avoid}\n"
                    f"Write {count} distinct, specific post drafts on different subjects."
                ),
            },
        ],
    )
