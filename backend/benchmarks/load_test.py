"""
Load testing for SWV endpoints using async httpx.
Simulates concurrent users hitting critical endpoints and reports latency percentiles.
"""
import asyncio
import json
import sys
import time
import statistics
from pathlib import Path
from typing import Any
from datetime import datetime

try:
    import httpx
except ImportError:
    print("httpx not installed. Run: pip install httpx")
    sys.exit(1)

CONCURRENCIES = [10, 50, 100, 200]
ENDPOINTS = [
    {"name": "health", "method": "GET", "url": "/api/v1/health"},
    {"name": "analyze-smoke", "method": "POST", "url": "/api/v1/analyze-smoke"},
    {"name": "reports-history", "method": "GET", "url": "/api/v1/reports/history"},
]
REQUESTS_PER_USER = 20
BASE_URL = "http://localhost:8000"
API_KEY = "test-benchmark-key"
SAMPLE_IMAGE_PATH = None


def _build_request(client: httpx.AsyncClient, ep: dict) -> tuple:
    headers = {"X-API-Key": API_KEY}
    if ep["method"] == "GET":
        if ep["name"] == "reports-history":
            params = {"latitude": 41.9028, "longitude": 12.4964, "days": 7, "limit": 10}
            return client.build_request("GET", ep["url"], headers=headers, params=params)
        return client.build_request("GET", ep["url"], headers=headers)
    if ep["name"] == "analyze-smoke":
        params_s = {"latitude": 41.9028, "longitude": 12.4964, "confidence": 0.5}
        if SAMPLE_IMAGE_PATH and Path(SAMPLE_IMAGE_PATH).exists():
            files = {"file": open(SAMPLE_IMAGE_PATH, "rb")}
            return client.build_request("POST", ep["url"], headers=headers, params=params_s, files=files)
        return client.build_request("POST", ep["url"], headers=headers, params=params_s)
    return client.build_request("GET", ep["url"], headers=headers)


async def _run_single_user(
    client: httpx.AsyncClient, ep: dict, results: list, user_id: int
):
    for _ in range(REQUESTS_PER_USER):
        try:
            req = _build_request(client, ep)
            start = time.perf_counter()
            resp = await client.send(req)
            elapsed = (time.perf_counter() - start) * 1000
            results.append(
                {
                    "latency_ms": elapsed,
                    "status": resp.status_code,
                    "success": resp.status_code < 500,
                }
            )
        except Exception:
            results.append({"latency_ms": None, "status": 0, "success": False})


async def _load_test_endpoint(concurrency: int, ep: dict) -> dict:
    results = []
    async with httpx.AsyncClient(timeout=60.0, base_url=BASE_URL) as client:
        tasks = [
            _run_single_user(client, ep, results, uid)
            for uid in range(concurrency)
        ]
        start_wall = time.perf_counter()
        await asyncio.gather(*tasks)
        wall_sec = time.perf_counter() - start_wall

    latencies = sorted([r["latency_ms"] for r in results if r["latency_ms"] is not None])
    successes = [r for r in results if r["success"]]
    total = len(results)
    ok_count = len(successes)

    def percentile(data, p):
        if not data:
            return 0.0
        idx = max(0, min(len(data) - 1, int(len(data) * p / 100)))
        return round(data[idx], 2)

    stats = {
        "endpoint": ep["name"],
        "concurrency": concurrency,
        "total_requests": total,
        "successful": ok_count,
        "failed": total - ok_count,
        "error_rate_pct": round((total - ok_count) / total * 100, 2) if total else 0,
        "total_duration_sec": round(wall_sec, 2),
        "requests_per_sec": round(total / wall_sec, 2) if wall_sec else 0,
        "latency_ms": {
            "min": round(min(latencies), 2) if latencies else 0,
            "p50": percentile(latencies, 50),
            "p95": percentile(latencies, 95),
            "p99": percentile(latencies, 99),
            "max": round(max(latencies), 2) if latencies else 0,
            "avg": round(statistics.mean(latencies), 2) if latencies else 0,
            "stdev": round(statistics.stdev(latencies), 2) if len(latencies) > 1 else 0,
        },
    }
    return stats


async def run_load_tests(concurrencies: list[int] | None = None) -> list[dict]:
    if concurrencies is None:
        concurrencies = CONCURRENCIES
    all_results = []
    for c in concurrencies:
        for ep in ENDPOINTS:
            print(f"  Load test: {ep['name']} @ {c} concurrent users ...", end=" ")
            sys.stdout.flush()
            stats = await _load_test_endpoint(c, ep)
            all_results.append(stats)
            print(f"done ({stats['requests_per_sec']} req/s, p95={stats['latency_ms']['p95']}ms)")
    return all_results


def save_report(results: list[dict], path: str = "load_test_report.json"):
    report = {
        "generated_at": datetime.utcnow().isoformat(),
        "config": {
            "concurrencies": CONCURRENCIES,
            "endpoints": [e["name"] for e in ENDPOINTS],
            "requests_per_user": REQUESTS_PER_USER,
            "base_url": BASE_URL,
        },
        "results": results,
    }
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Report saved to {path}")
    return report


def print_summary(results: list[dict]):
    print("\n" + "=" * 80)
    print("LOAD TEST SUMMARY")
    print("=" * 80)
    for r in results:
        lat = r["latency_ms"]
        print(
            f"  {r['endpoint']:25s} | concurrency={r['concurrency']:3d} | "
            f"req/s={r['requests_per_sec']:8.1f} | "
            f"p50={lat['p50']:7.1f}ms p95={lat['p95']:7.1f}ms p99={lat['p99']:7.1f}ms | "
            f"errors={r['error_rate_pct']:5.2f}%"
        )


async def main():
    print("SWV Load Testing")
    print("-" * 40)
    results = await run_load_tests()
    print_summary(results)
    save_report(results)
    return results


if __name__ == "__main__":
    asyncio.run(main())
