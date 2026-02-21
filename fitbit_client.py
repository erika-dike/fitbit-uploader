"""Fitbit API client — fetches all health metrics for a given date."""

from datetime import date

import fitbit_auth

BASE = "https://api.fitbit.com"


def _get(session, path):
    """Make a GET request and return the JSON response."""
    resp = session.get(f"{BASE}{path}")
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Individual metric fetchers
# ---------------------------------------------------------------------------

def get_activity_summary(session, d: date):
    """Daily activity summary: steps, distance, floors, calories."""
    data = _get(session, f"/1/user/-/activities/date/{d}.json")
    s = data.get("summary", {})
    return {
        "steps": s.get("steps", 0),
        "distance_km": _total_distance(s),
        "floors": s.get("floors", 0),
        "calories_total": s.get("caloriesOut", 0),
        "calories_activity": s.get("activityCalories", 0),
    }


def _total_distance(summary):
    """Sum all distance entries (km)."""
    distances = summary.get("distances", [])
    for d in distances:
        if d.get("activity") == "total":
            return round(d.get("distance", 0), 2)
    return 0


def get_azm(session, d: date):
    """Active Zone Minutes for the day."""
    data = _get(session, f"/1/user/-/activities/active-zone-minutes/date/{d}/1d.json")
    minutes = data.get("activities-active-zone-minutes", [])
    if not minutes:
        return {"azm_fat_burn": 0, "azm_cardio": 0, "azm_peak": 0, "azm_total": 0}
    val = minutes[0].get("value", {})
    return {
        "azm_fat_burn": val.get("fatBurnActiveZoneMinutes", 0),
        "azm_cardio": val.get("cardioActiveZoneMinutes", 0),
        "azm_peak": val.get("peakActiveZoneMinutes", 0),
        "azm_total": val.get("activeZoneMinutes", 0),
    }


def get_sleep(session, d: date):
    """Sleep data for the night ending on date d."""
    data = _get(session, f"/1.2/user/-/sleep/date/{d}.json")
    sleeps = data.get("sleep", [])
    # Use the "main" sleep entry (longest / primary)
    main = None
    for s in sleeps:
        if s.get("isMainSleep"):
            main = s
            break
    if not main and sleeps:
        main = sleeps[0]
    if not main:
        return {
            "sleep_start": "", "sleep_end": "",
            "sleep_duration_hrs": 0, "sleep_efficiency": 0,
            "sleep_deep_min": 0, "sleep_light_min": 0,
            "sleep_rem_min": 0, "sleep_wake_min": 0,
        }

    summary = main.get("levels", {}).get("summary", {})
    duration_ms = main.get("duration", 0)

    return {
        "sleep_start": main.get("startTime", ""),
        "sleep_end": main.get("endTime", ""),
        "sleep_duration_hrs": round(duration_ms / 3_600_000, 2),
        "sleep_efficiency": main.get("efficiency", 0),
        "sleep_deep_min": summary.get("deep", {}).get("minutes", 0),
        "sleep_light_min": summary.get("light", {}).get("minutes", 0),
        "sleep_rem_min": summary.get("rem", {}).get("minutes", 0),
        "sleep_wake_min": summary.get("wake", {}).get("minutes", 0),
    }


def get_heart_rate(session, d: date):
    """Resting heart rate from heart rate time series."""
    data = _get(session, f"/1/user/-/activities/heart/date/{d}/1d.json")
    entries = data.get("activities-heart", [])
    if not entries:
        return {"rhr": ""}
    val = entries[0].get("value", {})
    return {"rhr": val.get("restingHeartRate", "")}


def get_hrv(session, d: date):
    """Heart rate variability (RMSSD)."""
    data = _get(session, f"/1/user/-/hrv/date/{d}.json")
    entries = data.get("hrv", [])
    if not entries:
        return {"hrv_rmssd": ""}
    val = entries[0].get("value", {})
    return {"hrv_rmssd": round(val.get("dailyRmssd", 0), 2) if val.get("dailyRmssd") else ""}


def get_spo2(session, d: date):
    """Blood oxygen saturation."""
    data = _get(session, f"/1/user/-/spo2/date/{d}.json")
    # Response can be a dict with a single entry or a list
    val = data.get("value", data)
    if isinstance(val, list):
        val = val[0] if val else {}
    return {
        "spo2_avg": val.get("avg", ""),
        "spo2_min": val.get("min", ""),
        "spo2_max": val.get("max", ""),
    }


def get_breathing_rate(session, d: date):
    """Breathing rate during sleep."""
    data = _get(session, f"/1/user/-/br/date/{d}.json")
    entries = data.get("br", [])
    if not entries:
        return {"breathing_rate": ""}
    val = entries[0].get("value", {})
    return {"breathing_rate": round(val.get("breathingRate", 0), 1) if val.get("breathingRate") else ""}


def get_skin_temp(session, d: date):
    """Skin temperature variation from baseline."""
    data = _get(session, f"/1/user/-/temp/skin/date/{d}.json")
    entries = data.get("tempSkin", [])
    if not entries:
        return {"skin_temp_variation": ""}
    val = entries[0].get("value", {})
    return {"skin_temp_variation": val.get("nightlyRelative", "")}


def get_vo2_max(session, d: date):
    """Cardio fitness score (VO2 Max)."""
    data = _get(session, f"/1/user/-/cardioscore/date/{d}.json")
    entries = data.get("cardioScore", [])
    if not entries:
        return {"vo2_max": ""}
    val = entries[0].get("value", {})
    # Can be a range (vo2Max with low/high) or a single value
    vo2 = val.get("vo2Max")
    if isinstance(vo2, dict):
        low = vo2.get("low", "")
        high = vo2.get("high", "")
        return {"vo2_max": f"{low}-{high}"}
    return {"vo2_max": vo2 if vo2 else ""}


def get_exercises(session, d: date):
    """Today's exercise logs as a summary string."""
    data = _get(
        session,
        f"/1/user/-/activities/list.json?afterDate={d}&sort=asc&offset=0&limit=20",
    )
    activities = data.get("activities", [])
    if not activities:
        return {"exercises": "None"}

    parts = []
    for a in activities:
        # Only include activities from the target date
        log_date = a.get("startDate", a.get("originalStartTime", ""))[:10]
        if log_date != str(d):
            continue
        name = a.get("activityName", "Unknown")
        duration_min = round(a.get("activeDuration", 0) / 60000, 1)
        cals = a.get("calories", 0)
        parts.append(f"{name} ({duration_min}min, {cals}cal)")

    return {"exercises": "; ".join(parts) if parts else "None"}


# ---------------------------------------------------------------------------
# Aggregate fetcher
# ---------------------------------------------------------------------------

def fetch_all(d: date = None):
    """Fetch all metrics for the given date (defaults to today).

    Returns a flat dict ready for sheet writing.
    """
    if d is None:
        d = date.today()

    session = fitbit_auth.get_session()

    row = {}
    fetchers = [
        get_activity_summary,
        get_azm,
        get_sleep,
        get_heart_rate,
        get_hrv,
        get_spo2,
        get_breathing_rate,
        get_skin_temp,
        get_vo2_max,
        get_exercises,
    ]

    for fn in fetchers:
        try:
            row.update(fn(session, d))
        except Exception as e:
            print(f"Warning: {fn.__name__} failed: {e}")

    return row
