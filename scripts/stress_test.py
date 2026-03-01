from __future__ import annotations

import argparse
import json
import random
import statistics
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_VIBE_PROMPTS = [
    "I want something warm, easy, and uplifting tonight",
    "Low-stress vibe with heart and good pacing",
    "I need a comfort watch with high rewatch value",
    "I want a feel-good pick that is not childish",
    "Give me a cozy but smart recommendation",
    "I need a high-quality movie for winding down",
    "Something emotionally safe but still engaging",
    "A fun, polished movie I can trust",
    "I want a confident crowd-pleaser with substance",
    "Pick a quality comfort title that is easy to get into",
    "I want a positive tone without being cheesy",
    "I need a movie that leaves me in a better mood",
    "Give me something charming and not too heavy",
    "I want something acclaimed but accessible",
    "A low-friction watch with strong ratings",
    "I want an easy watch that still feels meaningful",
    "Something modern and uplifting with momentum",
    "A high-quality vibe watch, no stress",
    "I want a reliable, warm recommendation for tonight",
    "Give me a good movie when I do not want to overthink",
]


def _request_json(url: str, payload: dict[str, Any], timeout: float = 120.0) -> tuple[int, dict[str, Any], float]:
    started = time.perf_counter()
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
            elapsed_ms = (time.perf_counter() - started) * 1000
            return int(response.status), body, elapsed_ms
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        parsed = json.loads(body) if body else {}
        elapsed_ms = (time.perf_counter() - started) * 1000
        return int(exc.code), parsed, elapsed_ms


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]

    ordered = sorted(values)
    rank = max(0, min(len(ordered) - 1, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return ordered[rank]


def _summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(records)
    successes = [row for row in records if row["status"] == 200]
    failures = [row for row in records if row["status"] != 200]

    latencies = [row["latency_ms"] for row in successes]
    years = [row["year"] for row in successes if isinstance(row.get("year"), int)]
    titles = [row["title"] for row in successes if row.get("title")]

    reroll_pairs = {}
    for row in records:
        pair_key = row.get("pair_id")
        if pair_key is None:
            continue
        reroll_pairs.setdefault(pair_key, []).append(row)

    reroll_total = 0
    reroll_diff = 0
    for pair in reroll_pairs.values():
        if len(pair) != 2:
            continue
        first, second = sorted(pair, key=lambda x: x["attempt"])
        if first["status"] == 200 and second["status"] == 200:
            reroll_total += 1
            if first.get("title") != second.get("title"):
                reroll_diff += 1

    failure_counter = Counter()
    for row in failures:
        detail = row.get("error") or "unknown"
        detail = str(detail).split("\n", 1)[0][:180]
        failure_counter[detail] += 1

    summary = {
        "total_requests": total,
        "successful_requests": len(successes),
        "failed_requests": len(failures),
        "success_rate": round((len(successes) / total) if total else 0.0, 4),
        "latency_ms": {
            "p50": round(_percentile(latencies, 50), 2),
            "p90": round(_percentile(latencies, 90), 2),
            "p95": round(_percentile(latencies, 95), 2),
            "avg": round((sum(latencies) / len(latencies)) if latencies else 0.0, 2),
        },
        "diversity": {
            "unique_titles": len(set(titles)),
            "total_titles": len(titles),
            "unique_ratio": round((len(set(titles)) / len(titles)) if titles else 0.0, 4),
            "top_titles": Counter(titles).most_common(10),
        },
        "year_stats": {
            "min": min(years) if years else None,
            "median": int(statistics.median(years)) if years else None,
            "max": max(years) if years else None,
            "before_1960_count": sum(1 for year in years if year < 1960),
            "before_1960_ratio": round((sum(1 for year in years if year < 1960) / len(years)) if years else 0.0, 4),
        },
        "reroll": {
            "evaluated_pairs": reroll_total,
            "changed_title_pairs": reroll_diff,
            "change_rate": round((reroll_diff / reroll_total) if reroll_total else 0.0, 4),
        },
        "errors": failure_counter.most_common(10),
    }
    return summary


def _load_prompts(custom_file: str | None) -> list[str]:
    if not custom_file:
        return list(DEFAULT_VIBE_PROMPTS)

    path = Path(custom_file)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Prompt file must be a JSON array of strings")

    prompts: list[str] = []
    for item in payload:
        if isinstance(item, str) and item.strip():
            prompts.append(item.strip())
    if not prompts:
        raise ValueError("Prompt file contained no valid prompt strings")

    return prompts


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch stress test /recommend and optional rerolls")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="API base URL")
    parser.add_argument("--requests", type=int, default=20, help="Number of base recommendation requests")
    parser.add_argument("--with-rerolls", action="store_true", help="Issue a reroll after each base request")
    parser.add_argument("--format", default="any", choices=["any", "movie", "tv", "episode"])
    parser.add_argument("--length", default="any", choices=["any", "quick", "standard", "long", "epic"])
    parser.add_argument("--session-prefix", default="stress", help="Session id prefix")
    parser.add_argument("--prompt-file", default=None, help="Optional JSON file with prompt strings")
    parser.add_argument("--seed", type=int, default=7, help="Random seed")
    parser.add_argument("--output", default="stress_report.json", help="Output JSON report file")
    args = parser.parse_args()

    if args.requests <= 0:
        raise ValueError("--requests must be > 0")

    random.seed(args.seed)
    prompts = _load_prompts(args.prompt_file)

    records: list[dict[str, Any]] = []
    endpoint = args.base_url.rstrip("/") + "/recommend"

    for i in range(args.requests):
        prompt = random.choice(prompts)
        session_id = f"{args.session_prefix}-{i // 2 if args.with_rerolls else i}"

        payload = {
            "mood_input": prompt,
            "session_id": session_id,
            "format": args.format,
            "length": args.length,
            "reroll_of": None,
            "excluded_tmdb_ids": [],
        }

        status, body, elapsed = _request_json(endpoint, payload)
        request_id = body.get("request_id")
        title = body.get("recommendation", {}).get("title") if isinstance(body, dict) else None
        year = body.get("recommendation", {}).get("year") if isinstance(body, dict) else None

        base_row = {
            "pair_id": i if args.with_rerolls else None,
            "attempt": 1,
            "status": status,
            "latency_ms": round(elapsed, 2),
            "session_id": session_id,
            "request_id": request_id,
            "prompt": prompt,
            "title": title,
            "year": year,
            "error": body.get("detail") if isinstance(body, dict) else str(body),
        }
        records.append(base_row)
        print(f"[{i+1}/{args.requests}] status={status} title={title} latency={elapsed:.0f}ms")

        if args.with_rerolls:
            reroll_payload = dict(payload)
            reroll_payload["reroll_of"] = request_id
            status2, body2, elapsed2 = _request_json(endpoint, reroll_payload)
            title2 = body2.get("recommendation", {}).get("title") if isinstance(body2, dict) else None
            year2 = body2.get("recommendation", {}).get("year") if isinstance(body2, dict) else None

            reroll_row = {
                "pair_id": i,
                "attempt": 2,
                "status": status2,
                "latency_ms": round(elapsed2, 2),
                "session_id": session_id,
                "request_id": body2.get("request_id") if isinstance(body2, dict) else None,
                "prompt": prompt,
                "title": title2,
                "year": year2,
                "error": body2.get("detail") if isinstance(body2, dict) else str(body2),
            }
            records.append(reroll_row)
            print(f"    reroll status={status2} title={title2} latency={elapsed2:.0f}ms")

    summary = _summarize(records)

    output = {
        "config": {
            "base_url": args.base_url,
            "requests": args.requests,
            "with_rerolls": args.with_rerolls,
            "format": args.format,
            "length": args.length,
            "session_prefix": args.session_prefix,
            "seed": args.seed,
        },
        "summary": summary,
        "records": records,
    }

    out_path = Path(args.output)
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=True), encoding="utf-8")

    print("\nSummary:")
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    print(f"\nReport written to: {out_path.resolve()}")

    if summary["failed_requests"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
