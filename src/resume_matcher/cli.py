"""CLI interface for the Resume Matcher."""

import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from resume_matcher.config import ConfigError
from resume_matcher.extractor import extract_job, extract_resume
from resume_matcher.scorer import score_match

app = typer.Typer(help="Resume-to-Job Matcher CLI")
console = Console()

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "output"


def _ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _read_file(path: Path) -> str:
    if not path.exists():
        console.print(f"[red]Error:[/red] File not found: {path}")
        raise typer.Exit(code=1)
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        console.print(f"[red]Error:[/red] File is empty: {path}")
        raise typer.Exit(code=1)
    return text


def _save_json(data: dict, filename: str) -> Path:
    _ensure_output_dir()
    out_path = OUTPUT_DIR / filename
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path


@app.command(name="extract-resume")
def extract_resume_cmd(
    path: Path = typer.Argument(..., help="Path to a resume .txt file"),
) -> None:
    """Extract structured data from a resume."""
    text = _read_file(path)
    try:
        resume = extract_resume(text)
    except ConfigError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]API error:[/red] {e}")
        raise typer.Exit(code=1)

    data = resume.model_dump()
    console.print_json(json.dumps(data, indent=2, ensure_ascii=False))

    out = _save_json(data, f"resume_{path.stem}.json")
    console.print(f"\n[green]Saved to {out}[/green]")


@app.command(name="extract-job")
def extract_job_cmd(
    path: Path = typer.Argument(..., help="Path to a job description .txt file"),
) -> None:
    """Extract structured data from a job description."""
    text = _read_file(path)
    try:
        job = extract_job(text)
    except ConfigError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]API error:[/red] {e}")
        raise typer.Exit(code=1)

    data = job.model_dump()
    console.print_json(json.dumps(data, indent=2, ensure_ascii=False))

    out = _save_json(data, f"job_{path.stem}.json")
    console.print(f"\n[green]Saved to {out}[/green]")


@app.command()
def match(
    resume_path: Path = typer.Argument(..., help="Path to a resume .txt file"),
    job_path: Path = typer.Argument(..., help="Path to a job description .txt file"),
) -> None:
    """Match a resume against a job description (full pipeline)."""
    resume_text = _read_file(resume_path)
    job_text = _read_file(job_path)

    try:
        console.print("[bold]Extracting resume...[/bold]")
        resume = extract_resume(resume_text)

        console.print("[bold]Extracting job description...[/bold]")
        job = extract_job(job_text)

        console.print("[bold]Scoring match...[/bold]")
        result = score_match(resume, job, resume_text, job_text)

    except ConfigError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]API error:[/red] {e}")
        raise typer.Exit(code=1)

    _print_match_result(result)

    data = result.model_dump()
    out = _save_json(data, f"match_{resume_path.stem}_vs_{job_path.stem}.json")
    console.print(f"\n[green]Saved to {out}[/green]")


@app.command()
def rank(
    resumes_folder: Path = typer.Argument(..., help="Folder containing resume .txt files"),
    job_path: Path = typer.Argument(..., help="Path to a job description .txt file"),
) -> None:
    """Rank all resumes in a folder against a job description."""
    if not resumes_folder.is_dir():
        console.print(f"[red]Error:[/red] Not a directory: {resumes_folder}")
        raise typer.Exit(code=1)

    resume_files = sorted(resumes_folder.glob("*.txt"))
    if not resume_files:
        console.print(f"[red]Error:[/red] No .txt files found in {resumes_folder}")
        raise typer.Exit(code=1)

    job_text = _read_file(job_path)

    try:
        console.print("[bold]Extracting job description...[/bold]")
        job = extract_job(job_text)

        results = []
        for rf in resume_files:
            console.print(f"[bold]Processing {rf.name}...[/bold]")
            resume_text = _read_file(rf)
            resume = extract_resume(resume_text)
            result = score_match(resume, job, resume_text, job_text)
            results.append(result)

    except ConfigError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]API error:[/red] {e}")
        raise typer.Exit(code=1)

    # Sort by overall score descending
    results.sort(key=lambda r: r.overall_score, reverse=True)

    _print_leaderboard(results, job.job_title)

    data = [r.model_dump() for r in results]
    out = _save_json(data, f"rank_vs_{job_path.stem}.json")
    console.print(f"\n[green]Saved to {out}[/green]")


def _print_match_result(result) -> None:
    """Print a single match result as a rich table."""
    table = Table(title=f"Match: {result.candidate_name} → {result.job_title}")
    table.add_column("Metric", style="bold")
    table.add_column("Score", justify="right")

    table.add_row("Overall", f"{result.overall_score:.1f}")
    table.add_row("Required Skills", f"{result.breakdown.required_skills_score:.1f}")
    table.add_row("Preferred Skills", f"{result.breakdown.preferred_skills_score:.1f}")
    table.add_row("Experience", f"{result.breakdown.experience_score:.1f}")
    table.add_row("Education", f"{result.breakdown.education_score:.1f}")

    console.print(table)
    console.print(f"\n[bold]Recommendation:[/bold] {result.recommendation}")
    console.print(f"[bold]Matched Skills:[/bold] {', '.join(result.matched_skills) or 'None'}")
    console.print(f"[bold]Missing Skills:[/bold] {', '.join(result.missing_skills) or 'None'}")
    if result.explanation:
        console.print(f"\n[bold]Explanation:[/bold]\n{result.explanation}")


def _print_leaderboard(results: list, job_title: str) -> None:
    """Print a ranked leaderboard table."""
    table = Table(title=f"Candidate Rankings for: {job_title}")
    table.add_column("Rank", justify="right", style="bold")
    table.add_column("Candidate")
    table.add_column("Score", justify="right")
    table.add_column("Recommendation")

    for i, r in enumerate(results, 1):
        color = "green" if r.recommendation == "strong_match" else (
            "yellow" if r.recommendation == "possible_match" else "red"
        )
        table.add_row(
            str(i),
            r.candidate_name,
            f"{r.overall_score:.1f}",
            f"[{color}]{r.recommendation}[/{color}]",
        )

    console.print(table)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
