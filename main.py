#!/usr/bin/env python3
"""Health Dashboard CLI — pull Fitbit data and log health metrics to Google Sheets."""

import argparse
import sys
from datetime import date

import fitbit_auth
import fitbit_client
import sheets_writer


def cmd_auth(args):
    """Run the Fitbit OAuth2 authorization flow."""
    fitbit_auth.authorize()


def cmd_fitbit(args):
    """Pull Fitbit metrics and append to the sheet."""
    target = args.date if args.date else date.today()
    print(f"Fetching Fitbit data for {target}...")
    metrics = fitbit_client.fetch_all(target)
    sheets_writer.append_fitbit(metrics)


def cmd_bp(args):
    """Log blood pressure readings.

    Usage: python main.py bp 120/80/65 118/78/62 115/76/60
    Each argument is systolic/diastolic/pulse.
    """
    readings = []
    for raw in args.readings:
        parts = raw.split("/")
        if len(parts) < 2:
            print(f"Error: Invalid BP format '{raw}'. Use systolic/diastolic or systolic/diastolic/pulse")
            sys.exit(1)
        reading = {
            "systolic": int(parts[0]),
            "diastolic": int(parts[1]),
            "pulse": int(parts[2]) if len(parts) > 2 else "",
            "notes": "",
        }
        readings.append(reading)

    sheets_writer.append_bp(readings)


def cmd_diet(args):
    """Log diet items.

    Usage: python main.py diet lunch "Vegetable mix" 200 "Boiled yam" 300 "Steak" 150
    Items are pairs of (food_item, weight_grams). An optional note can follow as a third element.
    """
    meal = args.meal
    raw = args.items

    if len(raw) < 2:
        print("Error: Provide at least one food item and weight. E.g.: python main.py diet lunch \"Rice\" 300")
        sys.exit(1)

    items = []
    i = 0
    while i < len(raw):
        food = raw[i]
        # Next should be weight in grams
        if i + 1 < len(raw):
            try:
                weight = int(raw[i + 1])
                i += 2
            except ValueError:
                # No weight provided, just a food name
                weight = ""
                i += 1
        else:
            weight = ""
            i += 1

        items.append({"food_item": food, "weight_grams": weight, "notes": ""})

    sheets_writer.append_diet(meal, items)


def main():
    parser = argparse.ArgumentParser(
        description="Health Dashboard — Fitbit metrics + manual health data to Google Sheets"
    )
    sub = parser.add_subparsers(dest="command")
    sub.required = True

    # auth
    p_auth = sub.add_parser("auth", help="Authorize with Fitbit (one-time browser flow)")
    p_auth.set_defaults(func=cmd_auth)

    # fitbit
    p_fitbit = sub.add_parser("fitbit", help="Pull Fitbit data and append to sheet")
    p_fitbit.add_argument(
        "--date", type=date.fromisoformat, default=None,
        help="Date to fetch (YYYY-MM-DD). Defaults to today.",
    )
    p_fitbit.set_defaults(func=cmd_fitbit)

    # bp
    p_bp = sub.add_parser("bp", help="Log blood pressure readings (systolic/diastolic/pulse)")
    p_bp.add_argument(
        "readings", nargs="+",
        help="One or more readings in systolic/diastolic/pulse format. E.g.: 120/80/65 118/78/62",
    )
    p_bp.set_defaults(func=cmd_bp)

    # diet
    p_diet = sub.add_parser("diet", help="Log diet items")
    p_diet.add_argument("meal", help="Meal name: breakfast, lunch, dinner, snack")
    p_diet.add_argument(
        "items", nargs="+",
        help='Pairs of "food_item" weight_grams. E.g.: "Vegetable mix" 200 "Boiled yam" 300',
    )
    p_diet.set_defaults(func=cmd_diet)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
