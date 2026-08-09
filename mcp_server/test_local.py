"""
test_local.py
-------------
Quick smoke test for the adapter layer. Run this BEFORE deploying so you can
prove the whole pipeline (geocode -> forecast -> derived logic) works without
touching Databricks at all.

    pip install -r requirements.txt
    python test_local.py

Screenshot the output for your submission — it demonstrates each tool path and
the error-handling path.
"""

import json
import datetime as dt

import weather_broker as wc


def show(title, obj):
    print(f"\n=== {title} ===")
    print(json.dumps(obj, indent=2, default=str))


if __name__ == "__main__":
    # 1. Current conditions
    show("get_current_weather('Chicago')", wc.fetch_current("Chicago"))

    # 2. Forecast
    show("get_forecast('Austin, TX', 3)", wc.fetch_forecast("Austin, TX", 3))

    # 3. Derived recommendation (tomorrow)
    tomorrow = (dt.date.today() + dt.timedelta(days=1)).isoformat()
    fc = wc.fetch_forecast("Chicago", days=16)
    day = next((d for d in fc["days"] if d["date"] == tomorrow), None)
    chance = day["precip_chance_pct"] if day else None
    show(
        f"umbrella logic for Chicago on {tomorrow}",
        {
            "date": tomorrow,
            "precip_chance_pct": chance,
            "umbrella_recommended": (chance is not None and chance >= 40),
            "threshold_pct": 40,
        },
    )

    # 4. Error-handling path (bad location returns a clean message, not a crash)
    try:
        wc.fetch_current("asdfghjkl-not-a-place")
    except wc.WeatherAPIError as exc:
        show("error handling (bad location)", {"error": str(exc)})
