"""
Profile each SWV endpoint with cProfile and generate flame-graph-compatible output.
Usage:
    python -m backend.scripts.profile_endpoints [--endpoint health]
"""
import argparse
import cProfile
import pstats
import io
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def _profile_sync(func, args=None, kwargs=None):
    pr = cProfile.Profile()
    pr.enable()
    func(*(args or ()), **(kwargs or {}))
    pr.disable()
    return pr


async def _profile_async(func, args=None, kwargs=None):
    import asyncio

    pr = cProfile.Profile()
    pr.enable()
    await func(*(args or ()), **(kwargs or {}))
    pr.disable()
    return pr


def _stats_to_dict(stats: pstats.Stats) -> dict:
    entries = []
    for func_key, (cc, nc, tt, ct, callers) in stats.stats.items():
        filename, lineno, func_name = func_key
        entries.append({
            "filename": filename,
            "lineno": lineno,
            "function": func_name,
            "ncalls": nc,
            "cumtime": round(ct, 4),
            "cumtime_percall": round(ct / nc, 4) if nc else 0,
            "tottime": round(tt, 4),
            "tottime_percall": round(tt / nc, 4) if nc else 0,
        })
    entries.sort(key=lambda x: x["cumtime"], reverse=True)
    return entries


def profile_endpoint(name: str) -> dict:
    print(f"Profiling endpoint: {name}")

    from backend.models.schemas import (
        SmokeAnalysis, SmokeLevel, PollutantReading, PollutantType,
        EnvironmentalReport, GeoLocation, AirQualitySummary,
    )
    from backend.services.air_quality import PollutantPredictor, SmokeAnalyzer

    import numpy as np

    dummy_img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    profile_globs = {
        "SmokeAnalyzer": SmokeAnalyzer,
        "PollutantPredictor": PollutantPredictor,
        "np": np,
        "dummy_img": dummy_img,
    }

    code_map = {
        "smoke_analysis": "SmokeAnalyzer.analyze_smoke_in_image(dummy_img)",
        "pollutant_estimation": (
            "sa = SmokeAnalyzer.analyze_smoke_in_image(dummy_img); "
            "PollutantPredictor.estimate_pollutants(sa)"
        ),
        "aqi_calculation": "PollutantPredictor._calculate_aqi(PollutantType.PM25, 45.0)",
        "report_generation": (
            "sa = SmokeAnalyzer.analyze_smoke_in_image(dummy_img); "
            "pr = PollutantPredictor.estimate_pollutants(sa); "
            "loc = GeoLocation(latitude=41.9, longitude=12.5, address='Rome'); "
            "PollutantPredictor.get_overall_aqi(pr)"
        ),
    }

    if name not in code_map:
        available = list(code_map.keys())
        print(f"Unknown endpoint '{name}'. Available: {available}")
        return {}

    pr = cProfile.Profile()
    pr.enable()
    for _ in range(100):
        exec(code_map[name], profile_globs)
    pr.disable()

    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats("cumtime")
    ps.print_stats(20)

    print("\nTop 20 functions by cumulative time:")
    print(s.getvalue())

    stats = _stats_to_dict(ps)
    result = {
        "endpoint": name,
        "profiled_at": datetime.utcnow().isoformat(),
        "total_cumtime": round(sum(e["cumtime"] for e in stats[:5]), 4),
        "top_functions": stats[:30],
    }

    out_path = Path(f"profile_{name}.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Profile data saved to {out_path}")

    return result


def profile_all():
    endpoints = [
        "smoke_analysis",
        "pollutant_estimation",
        "aqi_calculation",
        "report_generation",
    ]
    results = {}
    for ep in endpoints:
        results[ep] = profile_endpoint(ep)

    combined = {
        "generated_at": datetime.utcnow().isoformat(),
        "results": results,
    }
    with open("profile_all_endpoints.json", "w") as f:
        json.dump(combined, f, indent=2)
    print("All profiles saved to profile_all_endpoints.json")

    print("\n" + "=" * 60)
    print("PROFILING SUMMARY")
    print("=" * 60)
    for ep, data in results.items():
        if data:
            print(f"  {ep:25s}  total_cumtime={data['total_cumtime']:8.2f}s")


def generate_flamegraph_data(profile_data: dict, output: str = "flamegraph_data.txt"):
    functions = profile_data.get("top_functions", [])
    lines = []
    for f in functions:
        name = f"{f['filename']}:{f['lineno']} {f['function']}"
        val = int(f["cumtime"] * 1000)
        lines.append(f"{name} {val}")
    with open(output, "w") as f:
        f.write("\n".join(lines))
    print(f"Flame graph data ({len(lines)} samples) saved to {output}")
    print("Use: https://www.speedscope.app/ or Brendan Gregg's FlameGraph tools")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Profile SWV endpoints")
    parser.add_argument(
        "--endpoint", "-e",
        default="all",
        help="Endpoint to profile: smoke_analysis, pollutant_estimation, aqi_calculation, report_generation, or 'all'",
    )
    parser.add_argument(
        "--flamegraph", "-f",
        action="store_true",
        help="Generate flame graph data files",
    )
    args = parser.parse_args()

    if args.endpoint == "all":
        profile_all()
    else:
        data = profile_endpoint(args.endpoint)
        if args.flamegraph and data:
            generate_flamegraph_data(data)
