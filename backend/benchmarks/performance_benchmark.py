"""
Microbenchmarks for SWV critical paths using timeit.
Measures cache operations, Pydantic model creation, AQI calculation, and smoke analysis.
"""
import sys
import timeit
import json
import gc
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.services.cache import SimpleCache, CacheManager
from backend.models.schemas import (
    SmokeLevel, PollutantType, GeoLocation, EnvironmentalData,
    SmokeAnalysis, PollutantReading, AirQualitySummary, EnvironmentalReport,
)
from backend.services.air_quality import PollutantPredictor, SmokeAnalyzer

NUM_RUNS = 5


def _measure(code: str, globs: dict, repeat: int = NUM_RUNS, number: int = 2000) -> dict:
    gc.collect()
    timings = timeit.repeat(code, globals=globs, repeat=repeat, number=number)
    best = min(timings)
    avg = sum(timings) / len(timings)
    return {
        "best_ms": round(best / number * 1000, 4),
        "avg_ms": round(avg / number * 1000, 4),
        "calls_per_sec": round(number / best, 0),
    }


def benchmark_cache_ops():
    print("  [Cache]")
    cache = SimpleCache(max_size=10000)

    results = {}

    t = _measure(
        "cache.set('k', 'v')",
        {"cache": cache},
        number=5000,
    )
    results["set_1b"] = t

    cache.set("k", "v")
    t = _measure(
        "cache.get('k')",
        {"cache": cache},
        number=5000,
    )
    results["get_1b"] = t

    for size, label in [(100, "100b"), (1024, "1kb"), (10240, "10kb")]:
        val = "x" * size
        cache.set(f"ks{size}", val)
        t = _measure(
            f"cache.get('ks{size}')",
            {"cache": cache},
            number=2000,
        )
        results[f"get_{label}"] = t

    cache2 = SimpleCache(max_size=10000)
    for i in range(1000):
        cache2.set(f"bulk_{i}", "v" * 100)
    t = _measure(
        "cache2._cleanup_expired()",
        {"cache2": cache2},
        number=500,
    )
    results["cleanup_expired_1000"] = t

    return results


def benchmark_validation():
    print("  [Model Validation]")

    results = {}

    geo = GeoLocation(latitude=41.9, longitude=12.5, address="Rome")
    t = _measure(
        "GeoLocation(latitude=41.9, longitude=12.5, address='Rome')",
        {"GeoLocation": GeoLocation},
        number=3000,
    )
    results["GeoLocation_create"] = t

    t = _measure(
        "SmokeLevel.EXCELLENT, SmokeLevel.MODERATE, SmokeLevel.HAZARDOUS",
        {"SmokeLevel": SmokeLevel},
        number=5000,
    )
    results["SmokeLevel_enum"] = t

    pr_args = {
        "pollutant_type": PollutantType.PM25,
        "value": 35.0,
        "unit": "µg/m³",
        "aqi_index": 85,
        "risk_level": "moderate",
    }
    t = _measure(
        "PollutantReading(**pr_args)",
        {"PollutantReading": PollutantReading, "pr_args": pr_args},
        number=3000,
    )
    results["PollutantReading_create"] = t

    return results


def benchmark_aqi_calc():
    print("  [AQI Calculation]")

    results = {}

    for pollutant in [PollutantType.PM25, PollutantType.PM10, PollutantType.NO2]:
        name = pollutant.value.replace(".", "_")
        t = _measure(
            f"PollutantPredictor._calculate_aqi(PollutantType.{name}, 45.0)",
            {"PollutantPredictor": PollutantPredictor, "PollutantType": PollutantType},
            number=3000,
        )
        results[f"aqi_{name}"] = t

    t = _measure(
        "PollutantPredictor._determine_risk_level(85)",
        {"PollutantPredictor": PollutantPredictor},
        number=5000,
    )
    results["risk_level"] = t

    t = _measure(
        "PollutantPredictor.get_health_recommendations(85)",
        {"PollutantPredictor": PollutantPredictor},
        number=3000,
    )
    results["health_recs"] = t

    return results


def benchmark_smoke_analysis():
    print("  [Smoke Analysis]")
    results = {}

    dummy_img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    t = timeit.timeit(
        lambda: SmokeAnalyzer.analyze_smoke_in_image(dummy_img),
        number=50,
    )
    results["full_analysis"] = {
        "best_ms": round(t / 50 * 1000, 2),
        "avg_ms": round(t / 50 * 1000, 2),
        "calls_per_sec": round(50 / t, 0),
    }

    t = timeit.timeit(
        lambda: SmokeAnalyzer._categorize_smoke_level(35.0),
        number=10000,
    )
    results["categorize"] = {
        "best_ms": round(t / 10000 * 1000, 4),
        "avg_ms": round(t / 10000 * 1000, 4),
        "calls_per_sec": round(10000 / t, 0),
    }

    mask = cv2_inRange(dummy_img)
    t = timeit.timeit(
        lambda: SmokeAnalyzer._analyze_density_distribution(mask, (480, 640)),
        number=500,
    )
    results["density_distribution"] = {
        "best_ms": round(t / 500 * 1000, 2),
        "avg_ms": round(t / 500 * 1000, 2),
        "calls_per_sec": round(500 / t, 0),
    }

    return results


def cv2_inRange(img):
    lower = np.array([0, 0, 50])
    upper = np.array([180, 50, 200])
    import cv2
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
    return cv2.inRange(hsv, lower, upper)


def run_all():
    print("=" * 60)
    print("SWV PERFORMANCE BENCHMARKS")
    print("=" * 60)

    all_results = {}

    print("\n1. Cache Operations")
    all_results["cache"] = benchmark_cache_ops()

    print("\n2. Model Validation (Pydantic)")
    all_results["validation"] = benchmark_validation()

    print("\n3. AQI Calculation")
    all_results["aqi"] = benchmark_aqi_calc()

    print("\n4. Smoke Analysis")
    all_results["smoke_analysis"] = benchmark_smoke_analysis()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for category, metrics in all_results.items():
        print(f"\n  [{category}]")
        for name, m in metrics.items():
            print(f"    {name:30s} best={m['best_ms']:>8.2f}ms  avg={m['avg_ms']:>8.2f}ms  {m['calls_per_sec']:>8.0f} calls/s")

    report = {
        "generated_at": datetime.utcnow().isoformat(),
        "benchmarks": all_results,
    }
    out = Path("performance_benchmark_report.json")
    with open(out, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved to {out}")
    return all_results


if __name__ == "__main__":
    run_all()
