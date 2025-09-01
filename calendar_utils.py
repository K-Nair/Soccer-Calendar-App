from typing import Iterable, Optional, Union
from ics import Calendar, Event

def _calendar_from_df(df, competition_name: Optional[str] = None) -> Calendar:
    c = Calendar()
    comp_col = None
    for candidate in ("competition", "league"):
        if candidate in df.columns:
            comp_col = candidate
            break

    for _, row in df.iterrows():
        dt = row["date"]
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

def export_to_ics(matches: Union["pandas.DataFrame", Iterable[object]], filename: str, competition_name: Optional[str] = None):
    """Existing file-based export (CLI)."""
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
            e = Event()
            e.name = f"{m.home} vs {m.away}"
            e.begin = m.date
            if getattr(m, "competition", None) or competition_name:
                e.description = getattr(m, "competition", competition_name)
            cal.events.add(e)

    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(cal)

def calendar_text_from_df(df, competition_name: Optional[str] = None) -> str:
    """NEW: return .ics content as a string (for GUI download)."""
    cal = _calendar_from_df(df, competition_name)
    return str(cal)