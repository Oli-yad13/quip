<p align="center">
  <img src="quip-logo.svg" alt="quip" width="420">
</p>

<p align="center"><b>Scrape X for dev inspiration, draft posts in your own voice with a free LLM, and post them by hand.</b></p>

<p align="center">No paid API. No auto-posting. You stay the editor.</p>

---

Growing a developer presence on X means posting good things consistently — which
is hard. quip does the heavy lifting: it reads what your corner of the dev world
is talking about (your following feed + a big pool of dev accounts and topics),
drafts a handful of posts in **your** voice across different categories, and hands
them to you to review and post. You approve everything; nothing goes out on its own.

```
Your X following feed  ──┐
Top dev accounts        ─┤
Topic searches          ─┼──> free LLM drafts posts in YOUR voice ──> you review & post
Hacker News / dev.to    ─┘        (voice.md · topics.md · categories.md)
(fallback)
```

## Features

- **Reads your following feed** plus a pool of 30+ dev accounts and topic searches (sampled for variety each run).
- **Your voice, your topics, your categories** — three plain-text config files you control. Nothing is hardcoded.
- **Free to run** — drafting uses [GitHub Models](https://models.github.ai) (free with any GitHub account). No credit card, no OpenAI/Anthropic bill.
- **Human-in-the-loop** — you review every draft and post manually. No automation on your posting account.
- **Interactive session** — run `python main.py` for a clean `quip ›` prompt: type `draft`, `review`, `status`, drafts render as cards.

> ⚠️ **Scraping X is against its Terms of Service.** Use a **separate/throwaway**
> account for scraping — never the account you post from. Keep volume low. If the
> scraper breaks (X changes its UI), it falls back to the Hacker News + dev.to APIs.

## Quick start

```bash
# 1. Install
pip install -r requirements.txt
scrapling install            # one-time: downloads the stealth browser

# 2. Create your config from the templates
python main.py init          # makes voice.md, topics.md, categories.md, .env

# 3. Add a free GitHub token to .env  (GITHUB_TOKEN=...)
#    https://github.com/settings/tokens  ->  fine-grained  ->  Account: Models: read

# 4. Make your voice yours
#    edit voice.md (how you write), topics.md (your projects), categories.md (post types)

# 5. Log into X once (throwaway account) — a window opens, you sign in, it saves
python main.py login         # sign in; the session is saved to ./xprofile

# 6. Run it
python main.py               # interactive session: type draft, review, status, ...
```

### The session

```
quip > draft 3          # scrape your feed + write 3 drafts (shown as cards)
quip > about Fable 5     # draft posts about a SPECIFIC topic you pick
quip > about today's AI news
quip > review            # go through them: copy / mark posted / skip
quip > status            # counts
quip > login             # sign into X once (saves your session)
quip > edit voice        # tweak how you sound
quip > help              # all commands
quip > quit
```

`draft` follows your feed; `about <topic>` chases whatever's trending *today* —
type the thing (a new model drop, a framework release, some drama), and quip
searches X for what people are actually saying and drafts posts about exactly that.

## Configuration

| File | What it controls |
|------|------------------|
| `voice.md` | How you write — tone, rules, example posts. |
| `topics.md` | Who you are and what you're building (where post ideas come from). |
| `categories.md` | The kinds of posts to spread across (hot-take, build-in-public, tip, ...). |
| `xscrape.py` → `ACCOUNTS` / `TOPICS` | Which X accounts and searches to pull from. |
| `.env` | Your `GITHUB_TOKEN` (and optional `MODEL`). |

`init` seeds the first three from `*.example.md` templates. Your filled-in versions
are git-ignored, so your personal config never ends up in the repo.

## How it works

quip is a handful of small Python files, each with one job:

| File | Role |
|------|------|
| `main.py` | CLI entry + plain command dispatcher |
| `tui.py` | The interactive `quip ›` session (Rich UI, draft cards) |
| `core.py` | Glue — orchestrates scrape → draft, loads config & drafts |
| `xscrape.py` | **The scraper.** The only file that uses Scrapling's stealth browser to read X |
| `generate.py` | Sends scraped tweets to the LLM, writes drafts in your voice |
| `sources.py` | Fallback — Hacker News + dev.to APIs (no browser) when X is unavailable |

Flow of one `draft`:

```
you type `draft`            (tui.py / main.py)
        │
        ▼
core.py ──▶ xscrape.py      scrape X with a headless stealth browser (Scrapling)
        │        │
        │        └─ X unavailable? ──▶ sources.py   (Hacker News / dev.to)
        ▼
core.py ──▶ generate.py     LLM drafts posts in your voice ──▶ drafts/*.json
        │
        ▼
you `review` ──▶ copy the good ones ──▶ post by hand
```

All X scraping lives in **`xscrape.py`** — it launches the stealth browser, loads
X search / your home feed, and pulls tweet text out with CSS selectors like
`article[data-testid="tweet"]`. When X changes its markup, those selectors are
what need updating (PRs welcome).

## Commands

```bash
python main.py            # interactive session (recommended)
python main.py init       # create config from templates
python main.py login      # sign into X once (saves your session)
python main.py draft 3    # scrape + draft 3 posts
python main.py review     # copy the good ones, mark posted/skipped
python main.py status     # counts
python main.py edit voice # open a config file (voice|topics|categories|sources|env)
```

## How drafting stays free

It calls GitHub Models with your GitHub token — free for every account, no card.
Default model is `openai/gpt-5-chat` (most natural-sounding); set
`MODEL=openai/gpt-4o-mini` in `.env` for a higher free quota if you hit rate
limits. You can also point it at any OpenAI-compatible provider (Ollama, Groq,
OpenRouter, OpenAI) via `AI_BASE_URL` + `AI_API_KEY` — see `.env.example`.
(Note: GitHub Copilot has no script API; GitHub Models is the script-friendly equivalent.)

## Contributing

PRs welcome — especially fixes to the X selectors in `xscrape.py` when X changes
its UI, and new source/category ideas. Open an issue first for anything large.

## License

MIT — see [LICENSE](LICENSE).
