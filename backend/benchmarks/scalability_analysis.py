"""
Scalability analysis report generator for SWV.
Analyzes load test results and generates recommendations for:
- Database indexing
- Cache tuning
- Connection pool sizing
- Async worker count
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Any


def _load_json(path: str | Path) -> dict:
    with open(path) as f:
        return json.load(f)


def analyze_load_test(report_path: str = "load_test_report.json") -> dict:
    data = _load_json(report_path)
    results = data.get("results", [])
    if not results:
        print(f"No results found in {report_path}")
        return {}

    analysis = {
        "report": data.get("generated_at", "unknown"),
        "endpoints": {},
        "overall": {"max_rps": 0, "bottleneck_endpoint": None, "average_p95_ms": 0},
    }

    p95s = []
    for r in results:
        ep = r["endpoint"]
        if ep not in analysis["endpoints"]:
            analysis["endpoints"][ep] = []
        analysis["endpoints"][ep].append(r)
        p95s.append(r["latency_ms"]["p95"])
        if r["requests_per_sec"] > analysis["overall"]["max_rps"]:
            analysis["overall"]["max_rps"] = r["requests_per_sec"]

    ep_p95_avgs = {}
    for ep, entries in analysis["endpoints"].items():
        avg_p95 = sum(e["latency_ms"]["p95"] for e in entries) / len(entries)
        ep_p95_avgs[ep] = avg_p95

    bottleneck = max(ep_p95_avgs, key=ep_p95_avgs.get)
    analysis["overall"]["bottleneck_endpoint"] = bottleneck
    analysis["overall"]["average_p95_ms"] = round(sum(p95s) / len(p95s), 2) if p95s else 0
    return analysis


def generate_recommendations(analysis: dict) -> list[dict]:
    recs = []

    # --- Database Indexing ---
    recs.append({
        "category": "Database Indexing",
        "priority": "high",
        "recommendation": "Verify composite indexes on `historical_reports`: (latitude, longitude), (timestamp, latitude, longitude), (city, timestamp). These are already defined in ORM but should be validated with EXPLAIN QUERY PLAN on SQLite or EXPLAIN ANALYZE on PostgreSQL.",
        "rationale": "The /reports/history and /reports/stats/location endpoints query by lat/lon + timestamp range. Without covering indexes, these degrade to full table scans as data grows.",
        "action_items": [
            "Run `EXPLAIN QUERY PLAN SELECT ... FROM historical_reports WHERE latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ? AND timestamp BETWEEN ? AND ?` on SQLite",
            "Add index on (primary_pollutant) if stats queries become frequent",
            "Consider partial indexes for high-traffic city regions",
        ],
    })

    recs.append({
        "category": "Database Indexing",
        "priority": "medium",
        "recommendation": "Add composite index on `pollutant_readings`: (report_id, pollutant_type) to speed up JOIN queries when fetching full reports.",
        "rationale": "The `to_dict()` method lazy-loads pollutant_readings via relationship, but direct queries filtering by pollutant_type benefit from the index.",
        "action_items": [
            "Index already exists as idx_pollutant_report — verify usage",
        ],
    })

    # --- Cache Tuning ---
    recs.append({
        "category": "Cache Tuning",
        "priority": "high",
        "recommendation": "Increase SimpleCache max_size from 1000 to at least 10000 entries for production.",
        "rationale": "With only 1000 slots, the cache evicts entries aggressively under load (100 concurrent users hitting multiple endpoints can fill the cache in seconds). This causes most requests to miss cache and hit external APIs / database.",
        "action_items": [
            "Set max_size=10000 in backend/services/cache.py:SimpleCache.__init__",
            "Monitor cache hit rate via /api/v1/monitor/cache-stats",
            "Consider LRU eviction instead of oldest-expired for better hit rates",
        ],
    })

    recs.append({
        "category": "Cache Tuning",
        "priority": "medium",
        "recommendation": "Reduce geolocation TTL from 24h to 6h and weather TTL from 30min to 15min under high concurrency to avoid stale data serving.",
        "rationale": "While longer TTLs improve cache hit rate, they serve increasingly stale data. Under load, the cache fills quickly, and expired entries are only cleaned on set() when the cache is full.",
        "action_items": [
            "Add periodic background cleanup (every 60s) to remove expired entries proactively",
            "Implement cache sharding by endpoint type to prevent large weather entries from evicting geolocation entries",
        ],
    })

    # --- Connection Pool Sizing ---
    recs.append({
        "category": "Connection Pool Sizing",
        "priority": "high",
        "recommendation": "For PostgreSQL: increase pool_size from 10 to min(concurrent_users, 30) and max_overflow from 20 to 50.",
        "rationale": "Database.py configures pool_size=10, max_overflow=20 for PostgreSQL. At 200 concurrent users, many requests will queue waiting for a connection. With max_overflow=50, the effective pool size is 10+50=60, which still may be insufficient.",
        "action_items": [
            "Set pool_size=30 and max_overflow=50 in production",
            "For SQLite: keep StaticPool since it serializes writes (WAL mode helps reads)",
            "Add connection timeout: pool_timeout=30 to fail fast instead of queuing indefinitely",
            "Consider PgBouncer for connection pooling at the infrastructure level",
        ],
    })

    recs.append({
        "category": "Connection Pool Sizing",
        "priority": "low",
        "recommendation": "For /reports/history with large result sets: use streaming or paginated queries to avoid long-held connections.",
        "rationale": "Large queries block a connection from the pool for the duration of execution, reducing effective concurrency.",
        "action_items": [
            "Add pagination (offset/limit) to all list endpoints",
            "Consider server-side cursors for very large datasets",
        ],
    })

    # --- Async Worker Count ---
    recs.append({
        "category": "Async Worker Count",
        "priority": "high",
        "recommendation": "Run uvicorn with workers = 2 * CPU cores + 1, but no fewer than 4 for production.",
        "rationale": "The current main.py runs a single worker. With multiple workers, the application can handle more concurrent I/O-bound requests (external API calls, database queries). For CPU-bound YOLO inference, ensure workers don't exceed CPU cores to avoid thrashing.",
        "action_items": [
            "Launch with: uvicorn backend.main:app --workers 4 --loop uvloop",
            "For YOLO-heavy deployments: use 2 workers with a separate GPU process",
            "Set --limit-max-requests=10000 to prevent memory leaks from long-running workers",
        ],
    })

    recs.append({
        "category": "Async Worker Count",
        "priority": "medium",
        "recommendation": "Increase asyncio event loop's thread pool size for blocking operations (geocoding with geopy).",
        "rationale": "Operations like Nominatim reverse geocoding are synchronous and block the event loop. With concurrent users, this creates a bottleneck.",
        "action_items": [
            "Set ThreadPoolExecutor max_workers = workers * 10",
            "Move CPU-bound YOLO inference to a separate process pool",
        ],
    })

    # --- Identified Bottlenecks ---
    bottleneck = analysis.get("overall", {}).get("bottleneck_endpoint", "unknown")
    recs.append({
        "category": "Bottlenecks",
        "priority": "critical",
        "recommendation": f"Endpoint '{bottleneck}' identified as primary bottleneck in load tests. Investigate its latency profile.",
        "rationale": "The endpoint with the highest average p95 latency is the main bottleneck. Likely causes: external API calls (weather/geolocation), database queries, or YOLO inference.",
        "action_items": [
            f"Profile '{bottleneck}' with cProfile to identify hot spots",
            "Add detailed instrumentation (timing per sub-operation)",
            "Consider caching responses more aggressively",
            "Evaluate if the endpoint can be made async or if blocking calls can be moved to thread pools",
        ],
    })

    # --- YOLO Inference ---
    recs.append({
        "category": "YOLO Inference",
        "priority": "critical",
        "recommendation": "YOLO inference is CPU/GPU-bound and will block the async event loop. Offload to a separate process or use a queue-based architecture.",
        "rationale": "YOLO detection in detection.py runs synchronously in the main async loop. At 200 concurrent users with inference requests, the event loop is starved, drastically increasing latency for all endpoints.",
        "action_items": [
            "Run YOLO in a separate process via ProcessPoolExecutor",
            "Or use a task queue (Celery / RQ / ARQ) for inference offloading",
            "Implement request coalescing for identical images",
            "Use ONNX Runtime or TensorRT for faster inference",
        ],
    })

    return recs


def generate_report(
    load_test_path: str = "load_test_report.json",
    output_path: str = "scalability_analysis_report.json",
) -> dict:
    if not Path(load_test_path).exists():
        print(f"Load test report not found: {load_test_path}")
        print("Run load_test.py first to generate the input report.")
        return {}

    analysis = analyze_load_test(load_test_path)
    recommendations = generate_recommendations(analysis)

    report = {
        "generated_at": datetime.utcnow().isoformat(),
        "source_load_test": load_test_path,
        "load_test_summary": analysis.get("overall", {}),
        "recommendations": recommendations,
    }

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"Scalability analysis report saved to {output_path}")
    return report


def print_report(report: dict):
    if not report:
        return

    print("\n" + "=" * 70)
    print("SCALABILITY ANALYSIS REPORT")
    print("=" * 70)

    summary = report.get("load_test_summary", {})
    print(f"\nLoad Test Results:")
    print(f"  Max throughput:  {summary.get('max_rps', 'N/A'):>8.1f} req/s")
    print(f"  Bottleneck:      {summary.get('bottleneck_endpoint', 'N/A')}")
    print(f"  Average p95:     {summary.get('average_p95_ms', 'N/A'):>8.1f} ms")

    print(f"\nRecommendations:")
    for i, rec in enumerate(report.get("recommendations", []), 1):
        print(f"\n  [{rec['priority'].upper()}] {rec['category']}")
        print(f"  {rec['recommendation']}")
        for action in rec.get("action_items", []):
            print(f"    • {action}")


if __name__ == "__main__":
    lt_path = sys.argv[1] if len(sys.argv) > 1 else "load_test_report.json"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "scalability_analysis_report.json"
    report = generate_report(lt_path, out_path)
    print_report(report)
