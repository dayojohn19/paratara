import calendar
import re
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional


_WEEKDAY_TO_INDEX = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def _month_name_to_number(month_text: str) -> Optional[int]:
    if not month_text:
        return None

    normalized = re.sub(r"[^a-z]", "", month_text.strip().lower())
    if not normalized:
        return None

    # Try full names and abbreviations.
    for month_number in range(1, 13):
        if normalized == calendar.month_name[month_number].lower():
            return month_number
        if normalized == calendar.month_abbr[month_number].lower():
            return month_number

    return None


def _format_date_string(day: int, month: int, year: int) -> str:
    # Match the app's existing style (no leading zero days).
    return f"{calendar.month_abbr[month]} {day}, {year}"


def _dates_for_weekday_in_month(*, weekday_index: int, month: int, year: int) -> List[Dict]:
    result: List[Dict] = []
    _, days_in_month = calendar.monthrange(year, month)

    for day in range(1, days_in_month + 1):
        if date(year, month, day).weekday() == weekday_index:
            result.append(
                {
                    "dateN": day,
                    "monthN": month,
                    "yearN": year,
                    "date_string": _format_date_string(day, month, year),
                }
            )

    return result


# Matches:
# - "Every Friday in January 2026"
# - "every friday of jan 2026"
# - "Every Friday in January, 2026"
_EVERY_WEEKDAY_IN_MONTH_RE = re.compile(
    r"\bevery\s+"
    r"(?P<weekday>monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+"
    r"(?:in|of)\s+"
    r"(?P<month>[a-zA-Z]+)\s*,?\s*"
    r"(?P<year>\d{4})\b",
    re.IGNORECASE,
)


def expand_every_weekday_in_month(text: str) -> Optional[Dict]:
    """Expand patterns like "Every Friday in January 2026" into specific dates.

    Returns a dict in the same shape as the OpenAI extractor output, or None.
    """
    if not text:
        return None

    match = _EVERY_WEEKDAY_IN_MONTH_RE.search(text)
    if not match:
        return None

    weekday_raw = match.group("weekday")
    month_raw = match.group("month")
    year_raw = match.group("year")

    weekday_index = _WEEKDAY_TO_INDEX.get(weekday_raw.strip().lower())
    month_number = _month_name_to_number(month_raw)
    try:
        year_number = int(year_raw)
    except Exception:
        year_number = None

    if weekday_index is None or month_number is None or year_number is None:
        return None

    specific_dates = _dates_for_weekday_in_month(
        weekday_index=weekday_index,
        month=month_number,
        year=year_number,
    )

    return {
        "is_recurring": True,
        "is_multiple_dates": len(specific_dates) > 1,
        "recurring_pattern": f"Every {weekday_raw.title()} in {calendar.month_name[month_number]} {year_number}",
        "specific_dates": specific_dates,
    }
