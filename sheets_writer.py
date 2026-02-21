"""Google Sheets writer — appends rows to the Health Dashboard sheet."""

from datetime import datetime

import gspread

import config

# Column order must match the sheet headers exactly.
FITBIT_COLUMNS = [
    "steps", "distance_km", "floors", "calories_total", "calories_activity",
    "azm_fat_burn", "azm_cardio", "azm_peak", "azm_total",
    "sleep_start", "sleep_end", "sleep_duration_hrs", "sleep_efficiency",
    "sleep_deep_min", "sleep_light_min", "sleep_rem_min", "sleep_wake_min",
    "rhr", "hrv_rmssd", "spo2_avg", "spo2_min", "spo2_max",
    "breathing_rate", "skin_temp_variation", "vo2_max", "exercises",
]


def _get_sheet():
    """Authenticate and return the Google Sheet."""
    config._ensure_loaded()
    gc = gspread.service_account(filename=config.GOOGLE_SERVICE_ACCOUNT_FILE)
    return gc.open_by_key(config.GOOGLE_SHEET_ID)


def _timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def append_fitbit(metrics: dict):
    """Append a row of Fitbit metrics to the 'Fitbit' tab."""
    sheet = _get_sheet()
    ws = sheet.worksheet("Fitbit")
    row = [_timestamp()] + [metrics.get(col, "") for col in FITBIT_COLUMNS]
    ws.append_row(row, value_input_option="USER_ENTERED")
    print(f"Fitbit data appended ({row[0]})")


def append_bp(readings: list[dict]):
    """Append blood pressure readings to the 'Blood Pressure' tab.

    readings: list of dicts with keys: systolic, diastolic, pulse, notes
    """
    sheet = _get_sheet()
    ws = sheet.worksheet("Blood Pressure")
    ts = _timestamp()
    rows = []
    for i, r in enumerate(readings, 1):
        rows.append([
            ts,
            i,
            r.get("systolic", ""),
            r.get("diastolic", ""),
            r.get("pulse", ""),
            r.get("notes", ""),
        ])
    for row in rows:
        ws.append_row(row, value_input_option="USER_ENTERED")
    print(f"Blood pressure: {len(rows)} reading(s) appended ({ts})")


def append_diet(meal: str, items: list[dict]):
    """Append diet items to the 'Diet' tab.

    items: list of dicts with keys: food_item, weight_grams, notes
    """
    sheet = _get_sheet()
    ws = sheet.worksheet("Diet")
    ts = _timestamp()
    rows = []
    for item in items:
        rows.append([
            ts,
            meal.capitalize(),
            item.get("food_item", ""),
            item.get("weight_grams", ""),
            item.get("notes", ""),
        ])
    for row in rows:
        ws.append_row(row, value_input_option="USER_ENTERED")
    print(f"Diet: {len(rows)} item(s) appended for {meal} ({ts})")
