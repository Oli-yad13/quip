"""quip — scrape X for dev inspiration, draft posts in your voice, post by hand.

Run with no arguments for the interactive session:
    python main.py

Or call commands directly (handy for scripts / Task Scheduler):
    python main.py init       create your editable config from the templates
    python main.py login      sign into X once (opens a window, saves your session)
    python main.py draft [n]  scrape X + draft n posts (default 3)
    python main.py about <topic>  draft posts about a specific topic you pick
    python main.py review      read each draft, copy the good ones
    python main.py status      show counts of pending/posted drafts
    python main.py edit <name> open a config file (voice/topics/categories/sources/env)
"""

import sys

from dotenv import load_dotenv

import core

load_dotenv()


def cmd_init() -> None:
    made = core.init_config()
    print("Created: " + ", ".join(made) if made else "Config already exists — nothing to create.")
    print("\nNext: edit voice.md, topics.md, categories.md, and put your token in .env.")


def cmd_login() -> None:
    from xscrape import login
    login()


def _print_drafts(drafts: list[dict]) -> None:
    for d in drafts:
        tag = f"#{d.get('category', '')}" if d.get("category") else ""
        print(f"  [{len(d['text'])} chars] {tag}\n  {d['text']}\n")
    print("Run `python main.py review` (or the session) to copy and post them.")


def cmd_draft(count: int) -> None:
    print("Scraping X for inspiration...")
    drafts, n, fallback = core.scrape_and_generate(count)
    src = "Hacker News / dev.to (X fallback)" if fallback else "X"
    print(f"  drafted from {n} items via {src}.\n")
    _print_drafts(drafts)


def cmd_about(topic: str) -> None:
    print(f"Searching X for '{topic}'...")
    drafts, found = core.topic_and_generate(topic, 3)
    print(f"  read {found} posts about it.\n" if found else "  no X posts found; drafting from the name.\n")
    _print_drafts(drafts)


def cmd_review() -> None:
    pending = core.draft_files("pending")
    if not pending:
        print("No pending drafts. Run 'draft' first.")
        return
    for path in pending:
        record = core.load(path)
        tag = f"#{record.get('category', '')}" if record.get("category") else ""
        print("\n" + "=" * 60)
        print(record["text"])
        print(f"\n  ({len(record['text'])} chars · {tag} · inspired by: {record['inspiration']})")
        choice = input(
            "\n[c]opy / [m]ark posted / [s]kip / [n]ext / [q]uit? "
        ).strip().lower()
        if choice == "q":
            return
        if choice == "c":
            ok = core.copy_to_clipboard(record["text"])
            print("Copied — paste it into X." if ok else "Copy it manually.")
            record["status"] = "posted"
        elif choice == "m":
            record["status"] = "posted"
        elif choice == "s":
            record["status"] = "skipped"
        else:
            continue
        core.save(path, record)


def cmd_status() -> None:
    for status in ("pending", "posted", "skipped"):
        print(f"  {status}: {len(core.draft_files(status))}")


def cmd_edit(name: str) -> None:
    err = core.edit_config(name)
    print(err if err else f"Opened {name}.")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        from tui import run_session
        run_session()
    else:
        cmd = args[0]
        if cmd == "init":
            cmd_init()
        elif cmd in ("login", "browser"):
            cmd_login()
        elif cmd == "draft":
            cmd_draft(int(args[1]) if len(args) > 1 and args[1].isdigit() else 3)
        elif cmd == "about" and len(args) > 1:
            cmd_about(" ".join(args[1:]))
        elif cmd == "review":
            cmd_review()
        elif cmd == "status":
            cmd_status()
        elif cmd == "edit" and len(args) > 1:
            cmd_edit(args[1])
        else:
            print(__doc__)
