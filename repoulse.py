import argparse
import os
import subprocess
import sys
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def run_git(repo_path, args):
    try:
        res = subprocess.run(
            ["git", "-C", repo_path] + args,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode == 0:
            return res.stdout.strip()
        return None
    except Exception:
        return None


def find_git_repos(root_dir, max_depth=3):
    repos = []
    root_dir = os.path.abspath(root_dir)
    base_depth = root_dir.count(os.sep)

    for current_root, dirs, _ in os.walk(root_dir):
        current_depth = current_root.count(os.sep) - base_depth
        if current_depth > max_depth:
            dirs[:] = []
            continue

        if ".git" in dirs:
            repos.append(current_root)
            dirs[:] = []  # Non scendere dentro sottocartelle di un repo già trovato
            continue

        # Salta cartelle pesanti/inutili durante la scansione
        dirs[:] = [
            d for d in dirs
            if d not in {"node_modules", ".venv", "venv", "__pycache__", ".git", "Library", "AppData"}
        ]

    return sorted(repos)


def inspect_repo(repo_path):
    name = os.path.basename(repo_path)
    branch = run_git(repo_path, ["rev-parse", "--abbrev-ref", "HEAD"]) or "detached"
    status_raw = run_git(repo_path, ["status", "--porcelain"]) or ""

    modified = 0
    untracked = 0
    for line in status_raw.splitlines():
        if line.startswith("??"):
            untracked += 1
        elif line.strip():
            modified += 1

    dirty = (modified + untracked) > 0

    # Controlla ahead/behind rispetto all'upstream
    ahead = 0
    behind = 0
    upstream = run_git(repo_path, ["rev-parse", "--abbrev-ref", "@{u}"])
    if upstream:
        counts = run_git(repo_path, ["rev-list", "--left-right", "--count", f"{upstream}...HEAD"])
        if counts:
            parts = counts.split()
            if len(parts) == 2:
                behind = int(parts[0])
                ahead = int(parts[1])

    last_commit = run_git(repo_path, ["log", "-1", "--format=%cr — %s"]) or "No commits yet"
    remote_url = run_git(repo_path, ["remote", "get-url", "origin"]) or "No origin"

    return {
        "name": name,
        "path": repo_path,
        "branch": branch,
        "dirty": dirty,
        "modified": modified,
        "untracked": untracked,
        "ahead": ahead,
        "behind": behind,
        "last_commit": last_commit[:52] + ("..." if len(last_commit) > 52 else ""),
        "remote": remote_url,
    }


def render_dashboard(root_dir, repo_data):
    console.print(
        Panel(
            f"[bold cyan]Root:[/bold cyan] {root_dir}  |  "
            f"[bold green]Repos trovati:[/bold green] {len(repo_data)}  |  "
            f"[bold yellow]Scan:[/bold yellow] {datetime.now().strftime('%H:%M:%S')}",
            title="[bold magenta]🛰️  REPOPULSE — GIT WORKSPACE RADAR[/bold magenta]",
            border_style="bright_blue",
        )
    )

    table = Table(expand=True, border_style="dim")
    table.add_column("Repository", style="bold white", width=22)
    table.add_column("Branch", style="cyan", width=14)
    table.add_column("Working Tree", width=18)
    table.add_column("Sync", width=14)
    table.add_column("Ultimo Commit", style="dim white")

    dirty_count = 0
    ahead_count = 0

    for r in repo_data:
        if r["dirty"]:
            dirty_count += 1
            wt_status = f"[bold yellow]● {r['modified']}M / {r['untracked']}?[/bold yellow]"
        else:
            wt_status = "[green]✔ Clean[/green]"

        if r["ahead"] > 0:
            ahead_count += 1
            sync_status = f"[bold magenta]↑ {r['ahead']} ahead[/bold magenta]"
        elif r["behind"] > 0:
            sync_status = f"[bold red]↓ {r['behind']} behind[/bold red]"
        else:
            sync_status = "[green]✔ Synced[/green]"

        table.add_row(
            r["name"],
            r["branch"],
            wt_status,
            sync_status,
            r["last_commit"],
        )

    console.print(table)
    console.print(
        f"\n[bold]Riepilogo:[/bold] "
        f"[yellow]{dirty_count} con modifiche non salvate[/yellow] · "
        f"[magenta]{ahead_count} con commit da pushare[/magenta]\n"
    )


def push_all_ahead(repo_data):
    targets = [r for r in repo_data if r["ahead"] > 0 and not r["dirty"]]
    if not targets:
        console.print("[cyan]Nessun repository pulito con commit da pushare.[/cyan]")
        return

    for r in targets:
        console.print(f"[bold]Push di [cyan]{r['name']}[/cyan] ({r['branch']})...[/bold]")
        res = subprocess.run(["git", "-C", r["path"], "push"], capture_output=True, text=True)
        if res.returncode == 0:
            console.print(f"  [green]✔ Push completato su {r['name']}[/green]")
        else:
            console.print(f"  [red]✘ Errore push su {r['name']}:[/red] {res.stderr.strip()}")


def main():
    parser = argparse.ArgumentParser(description="RepoPulse: scanner e gestore rapido per repository Git locali.")
    parser.add_argument("path", nargs="?", default=".", help="Cartella radice da scansionare (default: cartella corrente)")
    parser.add_argument("--depth", type=int, default=3, help="Profondità massima di ricerca cartelle (default: 3)")
    parser.add_argument("--push-ahead", action="store_true", help="Esegue 'git push' sui repo puliti che hanno commit ahead")

    args = parser.parse_args()

    if not os.path.exists(args.path):
        console.print(f"[bold red]Percorso non trovato:[/bold red] {args.path}")
        sys.exit(1)

    repos = find_git_repos(args.path, max_depth=args.depth)
    if not repos:
        console.print(f"[yellow]Nessun repository Git trovato in '{args.path}' (profondità {args.depth}).[/yellow]")
        sys.exit(0)

    data = [inspect_repo(path) for path in repos]
    render_dashboard(os.path.abspath(args.path), data)

    if args.push_ahead:
        push_all_ahead(data)


if __name__ == "__main__":
    main()
