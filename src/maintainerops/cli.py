import os
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Optional

# Ensure UTF-8 output streams on Windows terminals without UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from maintainerops import __version__
from maintainerops.config import load_config
from maintainerops.engine import run_scan
from maintainerops.models.findings import FindingType
from maintainerops.reporters.html_report import render_html
from maintainerops.reporters.json_report import render_json
from maintainerops.reporters.markdown import render_markdown
from maintainerops.server.app import start_server

app = typer.Typer(
    name="maintainerops",
    help="Human-first, open-source repository maintenance and explainable triage toolkit.",
    add_completion=False,
)
console = Console()
err_console = Console(stderr=True)


@app.command()
def version():
    """Display the current MaintainerOps version."""
    console.print(f"[bold blue]MaintainerOps[/bold blue] version [green]{__version__}[/green]")


@app.command()
def scan(
    target: str = typer.Argument(
        ...,
        help="GitHub repository ('owner/repo') or local JSON fixture path ('fixtures/data.json')",
    ),
    format: str = typer.Option(
        "markdown",
        "--format",
        "-f",
        help="Report format: 'markdown', 'json', or 'html'",
    ),
    output: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="File path to save the generated report. If omitted, prints to console.",
    ),
    config_file: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to custom .maintainerops.yml configuration.",
    ),
):
    """Scan a repository or offline fixture and generate an explainable triage report."""
    cfg = load_config(config_file)
    err_console.print(f"[bold cyan]Scanning target:[/bold cyan] {target}")

    try:
        report = run_scan(target, cfg)
    except Exception as e:
        err_console.print(f"[bold red]Scan error:[/bold red] {e}")
        raise typer.Exit(code=1)

    fmt = format.lower()
    if fmt == "json":
        rendered = render_json(report)
    elif fmt == "html":
        rendered = render_html(report)
    else:
        rendered = render_markdown(report)

    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding="utf-8")
        err_console.print(f"[bold green]Report saved successfully to:[/bold green] {output}")
    else:
        if fmt == "json":
            print(rendered)
        else:
            console.print(rendered)


@app.command()
def dashboard(
    port: int = typer.Option(
        8080,
        "--port",
        "-p",
        help="Local port to serve the interactive web dashboard.",
    ),
    target: str = typer.Option(
        "tests/fixtures/enterprise_repo.json",
        "--target",
        "-t",
        help="Initial repository or fixture to load in dashboard.",
    ),
    no_browser: bool = typer.Option(
        False,
        "--no-browser",
        help="Do not automatically launch web browser on startup.",
    ),
):
    """Launch the interactive MaintainerOps Web Dashboard and REST API."""
    # Ensure default target exists; if not, fallback to sample_repo.json
    if not os.path.exists(target) and "/" not in target:
        fallback = "tests/fixtures/sample_repo.json"
        if os.path.exists(fallback):
            target = fallback

    url = f"http://127.0.0.1:{port}"
    err_console.print(
        Panel.fit(
            f"[bold blue]🛡️ MaintainerOps Interactive Dashboard[/bold blue]\n\n"
            f"[bold green]Dashboard URL:[/bold green] [link={url}]{url}[/link]\n"
            f"[bold yellow]Initial Target:[/bold yellow] {target}\n"
            f"[dim]Press Ctrl+C to terminate the local server.[/dim]",
            border_style="cyan",
        )
    )

    try:
        httpd = start_server(host="127.0.0.1", port=port)
    except OSError as e:
        err_console.print(f"[bold red]Failed to start server on port {port}:[/bold red] {e}")
        raise typer.Exit(code=1)

    if not no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        err_console.print("\n[yellow]Shutting down MaintainerOps Dashboard...[/yellow]")
    finally:
        httpd.server_close()


@app.command()
def health(
    target: str = typer.Argument(
        ...,
        help="GitHub repository ('owner/repo') or local JSON fixture path.",
    ),
    config_file: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to custom .maintainerops.yml configuration.",
    ),
):
    """Display an executive terminal scoreboard of repository health and triage bottlenecks."""
    cfg = load_config(config_file)
    try:
        report = run_scan(target, cfg)
    except Exception as e:
        err_console.print(f"[bold red]Error running health check:[/bold red] {e}")
        raise typer.Exit(code=1)

    m = report.metrics
    hs = report.health_summary or {}

    grade_colors = {
        "A+": "bold green",
        "A": "bold green",
        "B": "bold cyan",
        "C": "bold yellow",
        "D": "bold red",
        "F": "bold red on white",
    }
    color = grade_colors.get(m.health_grade, "bold white")

    # Executive Scoreboard Panel
    score_content = (
        f"[bold]Repository:[/bold] {report.repository}\n"
        f"[bold]Health Index:[/bold] [{color}]{m.health_score}/100[/{color}] (Grade: [{color}]{m.health_grade}[/{color}])\n"
        f"[bold]Triage Burden:[/bold] {hs.get('triage_burden', 'Low')}\n"
        f"[bold]Primary Bottleneck:[/bold] {hs.get('primary_bottleneck', 'None')}"
    )
    console.print(Panel(score_content, title="🛡️ MaintainerOps Health Scorecard", border_style="blue"))

    # Table of Breakdown Metrics
    table = Table(title="Triage Health Breakdown", show_header=True, header_style="bold magenta")
    table.add_column("Category", style="cyan")
    table.add_column("Score / Count", justify="right")
    table.add_column("Health Status")

    table.add_row(
        "Issue Quality Ratio",
        f"{hs.get('issue_quality_score', 100)}%",
        f"{m.incomplete_issues_count} incomplete issue(s)",
    )
    table.add_row(
        "PR Pipeline Health",
        f"{hs.get('pr_pipeline_score', 100)}%",
        f"{m.blocked_prs_count} blocked PR(s) (CI / conflicts)",
    )
    table.add_row(
        "Backlog Freshness",
        f"{hs.get('backlog_freshness_score', 100)}%",
        f"{m.stale_items_count} dormant / stale item(s)",
    )
    table.add_row(
        "Urgent / Sentiment Alerts",
        str(m.sentiment_alerts_count),
        "Critical community urgency" if m.sentiment_alerts_count > 0 else "Normal",
    )
    table.add_row(
        "Good First Issues",
        str(m.good_first_issues_count),
        "Available for newcomer onboarding",
    )

    console.print(table)


@app.command()
def draft(
    target: str = typer.Argument(
        ...,
        help="GitHub repository or fixture.",
    ),
    item_number: int = typer.Argument(
        ...,
        help="Issue or PR number to extract polite draft response for.",
    ),
):
    """Retrieve and display the drafted polite follow-up response for an issue or PR."""
    report = run_scan(target)
    matches = [f for f in report.findings if f.item_number == item_number and f.draft_response]

    if not matches:
        err_console.print(f"[yellow]No drafted triage response found for item #{item_number}.[/yellow]")
        return

    for f in matches:
        console.print(
            Panel(
                f"[bold cyan]Subject:[/bold cyan] {f.item_title}\n"
                f"[bold cyan]Action:[/bold cyan] {f.suggested_action}\n\n"
                f"[bold green]💬 Draft Reply:[/bold green]\n{f.draft_response}",
                title=f"Draft Reply for #{f.item_number}",
                border_style="green",
            )
        )


@app.command()
def export_dashboard(
    target: str = typer.Argument(
        ...,
        help="GitHub repository ('owner/repo') or local JSON fixture path.",
    ),
    output: str = typer.Option(
        "dashboard.html",
        "--output",
        "-o",
        help="Output HTML file path.",
    ),
):
    """Export a standalone, interactive single-file HTML triage dashboard."""
    report = run_scan(target)
    html_content = render_html(report)

    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_content, encoding="utf-8")
    err_console.print(f"[bold green]Dashboard exported successfully to:[/bold green] {output}")


if __name__ == "__main__":
    app()
