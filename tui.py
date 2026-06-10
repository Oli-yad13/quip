"""Interactive quip session — a Claude-Code-style terminal experience.

Launched by `python main.py` with no arguments. Type commands at the `quip ›`
prompt: draft, about, review, status, login, sources, edit, help, clear, quit.
"""

import sys

import core

from rich.console import Console, Group
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

try:  # make sure stars / arrows render on Windows terminals
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

console = Console()

MASCOT = "✦"  # the little quip spark

LOGO = r"""
  __ _ _   _(_)_ __
 / _` | | | | | '_ \
| (_| | |_| | | |_) |
 \__, |\__,_|_| .__/
    |_|        |_|
"""

# cyan -> magenta gradient, line by line
LOGO_PALETTE = ["bright_cyan", "cyan", "blue", "bright_magenta", "magenta"]

# A colour per post category, so cards are scannable at a glance.
CAT_COLORS = {
    "hot-take": "red", "build-in-public": "green", "learning-in-public": "cyan",
    "reaction": "yellow", "tip": "blue", "question": "magenta", "story": "white",
}

COMMANDS = {
    "draft": "Scrape X + write drafts (e.g. `draft 3`)",
    "about": "Draft about a topic YOU pick (e.g. `about Fable 5`, `about today's AI news`)",
    "review": "Go through pending drafts - copy / skip / post",
    "status": "Counts of pending / posted / skipped",
    "login": "Sign into X once (opens a window; saves your session for scraping)",
    "sources": "Show the source pool the scraper samples from",
    "edit": "Open a config file: edit voice | topics | categories | sources",
    "init": "Create your config from the templates",
    "help": "Show this list",
    "clear": "Clear the screen",
    "quit": "Exit (also: exit, q)",
}


def _welcome() -> None:
    logo_lines = [
        Text(line, style=f"bold {LOGO_PALETTE[i % len(LOGO_PALETTE)]}")
        for i, line in enumerate(LOGO.strip("\n").splitlines())
    ]
    tagline = Text.assemble(
        (f"{MASCOT} ", "bold yellow"),
        ("a short, clever remark", "dim italic"),
    )
    sub = Text("Scrape X for inspiration, draft posts in your voice, post by hand.", style="white")
    hint = Text.assemble(
        ("Type ", "dim"), ("draft", "bold green"), (" to begin, or ", "dim"),
        ("help", "bold green"), (" to see commands.", "dim"),
    )
    console.print(Panel(
        Group(*logo_lines, Text(""), tagline, sub, Text(""), hint),
        border_style="magenta", padding=(1, 3), title=f"[bold yellow]{MASCOT}[/] quip",
    ))


def _help() -> None:
    table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
    table.add_column(style="bold cyan")
    table.add_column(style="white")
    for name, desc in COMMANDS.items():
        table.add_row(name, desc)
    console.print(Panel(table, title="commands", border_style="dim", padding=(1, 2)))


def _draft_card(record: dict, index: int | None = None) -> Panel:
    cat = record.get("category", "")
    color = CAT_COLORS.get(cat, "white")
    head = Text()
    head.append(f"{MASCOT} ", style=f"bold {color}")
    if index is not None:
        head.append(f"#{index}  ", style="dim")
    if cat:
        head.append(f" {cat} ", style=f"bold {color} reverse")
    head.append(f"   {len(record['text'])} chars", style="dim")
    body = Text(f"\n{record['text']}\n", style="bold")
    insp = record.get("inspiration", "")
    if insp:
        body.append(f"\ninspired by: {insp}", style="dim italic")
    return Panel(Text.assemble(head, body), border_style=color, padding=(0, 2))


def _cmd_draft(arg: str) -> None:
    count = int(arg) if arg.isdigit() else 3
    console.print(f"[dim]Scraping X and drafting {count} posts...[/]")
    try:
        with console.status(f"[cyan]{MASCOT} scraping & drafting...[/]", spinner="star"):
            drafts, n, fallback = core.scrape_and_generate(count)
    except SystemExit as e:  # e.g. missing GITHUB_TOKEN
        console.print(Panel(str(e), title="setup needed", border_style="red"))
        return
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        return

    src = "Hacker News / dev.to (X fallback)" if fallback else "X"
    console.print(f"[dim]Drafted from {n} items via {src}.[/]\n")
    for d in drafts:
        console.print(_draft_card(d))
    console.print("\n[dim]Type[/] [bold]review[/] [dim]to copy and post them.[/]")


def _cmd_about(arg: str) -> None:
    topic = arg or console.input("  [dim]what should the posts be about?[/] ").strip()
    if not topic:
        return
    console.print(f"[dim]Finding what people are saying about[/] [bold]{topic}[/][dim]...[/]")
    try:
        with console.status(f"[cyan]{MASCOT} searching X for '{topic}'...[/]", spinner="star"):
            drafts, found = core.topic_and_generate(topic, 3)
    except SystemExit as e:
        console.print(Panel(str(e), title="setup needed", border_style="red"))
        return
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        return

    if found:
        console.print(f"[dim]Read {found} posts about it.[/]\n")
    else:
        console.print(f"[yellow]Found no X posts about '{topic}' (drafting from the name alone — "
                      "log into X for real material).[/]\n")
    for d in drafts:
        console.print(_draft_card(d))
    console.print("\n[dim]Type[/] [bold]review[/] [dim]to copy and post them.[/]")


def _cmd_review() -> None:
    pending = core.draft_files("pending")
    if not pending:
        console.print("[dim]No pending drafts. Type[/] [bold]draft[/] [dim]first.[/]")
        return
    for i, path in enumerate(pending, 1):
        record = core.load(path)
        console.print(_draft_card(record, index=i))
        choice = Prompt.ask(
            "  [bold]c[/]opy  [bold]m[/]ark posted  [bold]s[/]kip  [bold]n[/]ext  [bold]q[/]uit",
            choices=["c", "m", "s", "n", "q"], default="n", show_choices=False,
        )
        if choice == "q":
            return
        if choice == "c":
            ok = core.copy_to_clipboard(record["text"])
            console.print("[green]copied - paste into X[/]" if ok else "[yellow]copy manually[/]")
            record["status"] = "posted"
        elif choice == "m":
            record["status"] = "posted"
        elif choice == "s":
            record["status"] = "skipped"
        else:
            continue
        core.save(path, record)
    console.print("\n[green]Done reviewing.[/]")


def _cmd_status() -> None:
    table = Table(box=None)
    table.add_column("status", style="bold")
    table.add_column("count", justify="right")
    colors = {"pending": "yellow", "posted": "green", "skipped": "dim"}
    for s in ("pending", "posted", "skipped"):
        table.add_row(f"[{colors[s]}]{s}[/]", str(len(core.draft_files(s))))
    console.print(table)


def _cmd_sources() -> None:
    import xscrape
    console.print(
        f"[bold]{len(xscrape.QUERIES)}[/] sources in the pool; "
        f"[bold]{xscrape.SAMPLE_PER_RUN}[/] sampled per run; "
        f"following feed: [bold]{'on' if xscrape.INCLUDE_FOLLOWING else 'off'}[/].\n"
        "[dim]Edit them with[/] [bold]edit sources[/][dim].[/]"
    )


def _cmd_edit(arg: str) -> None:
    if not arg:
        console.print("[dim]Usage:[/] edit voice | topics | categories | sources | env")
        return
    err = core.edit_config(arg)
    console.print(f"[red]{err}[/]" if err else f"[green]Opened {arg}.[/]")


def _cmd_init() -> None:
    made = core.init_config()
    console.print("[green]Created:[/] " + ", ".join(made) if made else "[dim]Config already exists.[/]")


def run_session() -> None:
    console.clear()
    _welcome()
    while True:
        try:
            raw = console.input(f"\n[bold yellow]{MASCOT}[/] [bold cyan]quip[/] [dim]›[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]bye[/]")
            return
        if not raw:
            continue
        cmd, _, arg = raw.partition(" ")
        cmd, arg = cmd.lower(), arg.strip()

        if cmd in ("quit", "exit", "q"):
            console.print("[dim]bye[/]")
            return
        elif cmd == "help":
            _help()
        elif cmd == "clear":
            console.clear(); _welcome()
        elif cmd == "draft":
            _cmd_draft(arg)
        elif cmd == "about":
            _cmd_about(arg)
        elif cmd == "review":
            _cmd_review()
        elif cmd == "status":
            _cmd_status()
        elif cmd in ("login", "browser"):
            from xscrape import login
            login()
        elif cmd == "sources":
            _cmd_sources()
        elif cmd == "edit":
            _cmd_edit(arg)
        elif cmd == "init":
            _cmd_init()
        else:
            console.print(f"[dim]Unknown command '{cmd}'. Type[/] [bold]help[/][dim].[/]")
