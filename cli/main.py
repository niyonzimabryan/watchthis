from __future__ import annotations

import json

import anyio
import typer

from core.errors import DependencyUnavailableError
from core.orchestrator import WatchThisOrchestrator
from data.models import FormatFilter, LengthFilter, RecommendationRequest, UserFilters


app = typer.Typer(help="WatchThis CLI")


def _orchestrator() -> WatchThisOrchestrator:
    return WatchThisOrchestrator.build_default()


def _print_response(response) -> None:
    typer.echo(json.dumps(response.model_dump(), indent=2, ensure_ascii=True))


@app.command("recommend")
def recommend(
    mood: str = typer.Option(..., "--mood", "-m", help="Mood input text"),
    session_id: str | None = typer.Option(None, "--session-id", help="Stable client/session identifier"),
    format_filter: FormatFilter = typer.Option(FormatFilter.ANY, "--format"),
    length_filter: LengthFilter = typer.Option(LengthFilter.ANY, "--length"),
    reroll_of: str | None = typer.Option(None, "--reroll-of"),
):
    async def _run() -> None:
        orchestrator = _orchestrator()
        request = RecommendationRequest(
            mood_input=mood,
            session_id=session_id,
            filters=UserFilters(format=format_filter, length=length_filter),
            is_roulette=False,
            is_reroll=bool(reroll_of),
            reroll_of=reroll_of,
        )
        try:
            response = await orchestrator.recommend(request)
            _print_response(response)
        except DependencyUnavailableError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(code=1)

    anyio.run(_run)


@app.command("roulette")
def roulette(
    session_id: str | None = typer.Option(None, "--session-id", help="Stable client/session identifier"),
    format_filter: FormatFilter = typer.Option(FormatFilter.ANY, "--format"),
    length_filter: LengthFilter = typer.Option(LengthFilter.ANY, "--length"),
    reroll_of: str | None = typer.Option(None, "--reroll-of"),
):
    async def _run() -> None:
        orchestrator = _orchestrator()
        request = RecommendationRequest(
            mood_input=None,
            session_id=session_id,
            filters=UserFilters(format=format_filter, length=length_filter),
            is_roulette=True,
            is_reroll=bool(reroll_of),
            reroll_of=reroll_of,
        )
        try:
            response = await orchestrator.recommend(request)
            _print_response(response)
        except DependencyUnavailableError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(code=1)

    anyio.run(_run)


if __name__ == "__main__":
    app()
