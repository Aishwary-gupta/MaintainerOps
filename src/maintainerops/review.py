import sys
from typing import List, Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from maintainerops.config import Config, load_config
from maintainerops.engine import run_scan
from maintainerops.models.findings import Finding
from maintainerops.state import is_dismissed, record_decision

console = Console()


def run_interactive_review(
    target: str,
    config: Optional[Config] = None,
    show_all: bool = False,
    use_ai: bool = False,
    input_func=None,
) -> None:
    """Runs a keyboard-driven interactive triage review loop over findings."""
    _input = input_func or input

    console.print(f"[bold cyan]Preparing interactive review for:[/bold cyan] {target}")
    report = run_scan(target, config, use_ai=use_ai)

    all_findings = report.findings
    if not show_all:
        findings: List[Finding] = [f for f in all_findings if not is_dismissed(f.id)]
    else:
        findings = list(all_findings)

    if not findings:
        console.print(
            Panel.fit(
                "🎉 [bold green]All caught up![/bold green] No active findings to review.\n"
                "[dim](Run with --all to include previously dismissed findings)[/dim]",
                border_style="green",
            )
        )
        return

    session_summary = {"accepted": 0, "edited": 0, "skipped": 0}
    total = len(findings)

    console.print(f"\n[bold]Starting Triage Queue ({total} item(s) to review)[/bold]")
    console.print("[dim]Options: [A]ccept | [E]dit draft | [S]kip & dismiss | [Q]uit[/dim]\n")

    for idx, f in enumerate(findings, start=1):
        item_label = "PR" if f.item_type == "pull_request" else "Issue"
        sev_color = "red" if f.severity in ["critical", "high"] else "yellow"

        # Evidence lines
        evidence_lines = []
        for ev in f.evidence:
            evidence_lines.append(f"  • [cyan]{ev.metric_name}:[/cyan] {ev.details}")
        evidence_str = "\n".join(evidence_lines) if evidence_lines else "  • No metric evidence attached"

        current_draft = f.draft_response or "No automated draft available."

        finding_panel = (
            f"[bold]{item_label} #{f.item_number}:[/bold] {f.item_title}\n"
            f"[dim]URL:[/dim] {f.item_url}\n"
            f"[dim]Type:[/dim] {f.finding_type}  |  "
            f"[dim]Severity:[/dim] [{sev_color}]{f.severity}[/{sev_color}]  |  "
            f"[dim]Confidence:[/dim] {int(f.confidence * 100)}%\n\n"
            f"[bold]Summary:[/bold] {f.summary}\n"
            f"[bold]Suggested Action:[/bold] {f.suggested_action}\n\n"
            f"[bold]Evidence Matrix:[/bold]\n{evidence_str}\n\n"
            f"[bold green]💬 Draft Response:[/bold green]\n"
            f"[italic]{current_draft}[/italic]"
        )

        console.print(
            Panel(
                finding_panel,
                title=f"Review Queue [{idx}/{total}]",
                border_style="blue",
            )
        )

        while True:
            try:
                prompt_text = "Choose action: [A]ccept  [E]dit  [S]kip/Dismiss  [Q]uit > "
                user_choice = _input(prompt_text).strip().lower()
            except (EOFError, KeyboardInterrupt):
                console.print("\n[yellow]Review session paused.[/yellow]")
                _print_summary(session_summary)
                return

            if user_choice in ["a", "accept"]:
                record_decision("accept", f, draft_response=current_draft)
                session_summary["accepted"] += 1
                console.print(f"[bold green]✓ Accepted draft for #{f.item_number}![/bold green]\n")
                break

            elif user_choice in ["e", "edit"]:
                console.print(f"\n[bold cyan]Original draft:[/bold cyan] {current_draft}")
                try:
                    new_draft = _input("Enter revised draft (or press enter to keep): ").strip()
                except (EOFError, KeyboardInterrupt):
                    new_draft = ""

                if new_draft:
                    current_draft = new_draft
                    record_decision("edit", f, draft_response=new_draft)
                    session_summary["edited"] += 1
                    console.print(f"[bold green]✓ Revised draft saved for #{f.item_number}![/bold green]\n")
                else:
                    record_decision("accept", f, draft_response=current_draft)
                    session_summary["accepted"] += 1
                    console.print(f"[bold green]✓ Kept original draft for #{f.item_number}![/bold green]\n")
                break

            elif user_choice in ["s", "skip", "dismiss"]:
                record_decision("skip", f)
                session_summary["skipped"] += 1
                console.print(f"[dim]Skipped & dismissed finding #{f.item_number}.[/dim]\n")
                break

            elif user_choice in ["q", "quit", "exit"]:
                console.print("\n[yellow]Exiting review queue...[/yellow]")
                _print_summary(session_summary)
                return

            else:
                console.print("[red]Invalid key. Please press A, E, S, or Q.[/red]")

    _print_summary(session_summary)


def _print_summary(summary: dict) -> None:
    table = Table(title="Triage Review Session Summary", border_style="cyan")
    table.add_column("Action", style="bold")
    table.add_column("Count", justify="right")

    table.add_row("Accepted Drafts", f"[green]{summary['accepted']}[/green]")
    table.add_row("Edited Drafts", f"[cyan]{summary['edited']}[/cyan]")
    table.add_row("Skipped / Dismissed", f"[dim]{summary['skipped']}[/dim]")

    console.print(table)
