from typing import Iterable, Optional, Union
from ics import Calendar, Event
from zoneinfo import ZoneInfo


# Map competition/league keywords to IANA timezones
LEAGUE_TZ_MAP = {
    "epl": "Europe/London",            # Premier League (BST/GMT)
    "premier": "Europe/London",
    "la-liga": "Europe/Madrid",        # Spain
    "laliga": "Europe/Madrid",
    "bundesliga": "Europe/Berlin",     # Germany
    "serie-a": "Europe/Rome",          # Italy
    "ligue-1": "Europe/Paris",         # France
    "ligue": "Europe/Paris",
    "eredivisie": "Europe/Amsterdam",  # Netherlands
    "champions": "Europe/Zurich",      # UEFA HQ
    "europa": "Europe/Zurich",
    "conference": "Europe/Zurich",
}


def _detect_timezone(competition_name: Optional[str]) -> ZoneInfo:
    """
    Given a competition/league label, return a ZoneInfo timezone.
    Defaults to UTC if unknown.
    """
    if not competition_name:
        return ZoneInfo("UTC")
    comp = competition_name.lower()
    for key, tz in LEAGUE_TZ_MAP.items():
        if key in comp:
            return ZoneInfo(tz)
    return ZoneInfo("UTC")


def _calendar_from_df(df, competition_name: Optional[str] = None) -> Calendar:
    c = Calendar()
    comp_col = None
    for candidate in ("competition", "league"):
        if candidate in df.columns:
            comp_col = candidate
            break

    # Pick a representative competition name to infer timezone
    comp_name = None
    if comp_col and not df.empty:
        comp_name = str(df[comp_col].iloc[0])
    if not comp_name:
        comp_name = competition_name or ""
    tz = _detect_timezone(comp_name)

    for _, row in df.iterrows():
        dt = row["date"]
        # If CSV dates are in local league time and naive, attach the league tz
        if getattr(dt, "tzinfo", None) is None:
            dt = dt.replace(tzinfo=tz)

        home = str(row["home team"])
        away = str(row["away team"])
        descr = (str(row[comp_col]) if comp_col else competition_name) or ""

        e = Event()
        e.name = f"{home} vs {away}"
        e.begin = dt
        if descr:
            e.description = descr
        c.events.add(e)
    return c


def export_to_ics(
    matches: Union["pandas.DataFrame", Iterable[object]],
    filename: str,
    competition_name: Optional[str] = None
):
    """Export matches to a file-based .ics."""
    try:
        import pandas as pd
        is_df = isinstance(matches, pd.DataFrame)
    except Exception:
        is_df = False

    if is_df:
        cal = _calendar_from_df(matches, competition_name)
    else:
        # iterable of objects with .date, .home, .away, .competition
        cal = Calendar()
        for m in matches:
            comp_name = getattr(m, "competition", None) or competition_name or ""
            tz = _detect_timezone(comp_name)
            dt = m.date
            if getattr(dt, "tzinfo", None) is None:
                dt = dt.replace(tzinfo=tz)

            e = Event()
            e.name = f"{m.home} vs {m.away}"
            e.begin = dt
            if getattr(m, "competition", None) or competition_name:
                e.description = getattr(m, "competition", competition_name)
            cal.events.add(e)

    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(cal)


def calendar_text_from_df(df, competition_name: Optional[str] = None) -> str:
    """Return .ics content as a string (for GUI download)."""
    cal = _calendar_from_df(df, competition_name)
    return str(cal)