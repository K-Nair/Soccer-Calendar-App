import pandas as pd
from pathlib import Path
from calendar_utils import export_to_ics
from rapidfuzz import process, fuzz


def choose_from_list(prompt, options):
    print(prompt)
    for i, option in enumerate(options, 1):
        print(f"{i}. {option}")
    raw = input("Enter numbers separated by commas or spaces (or leave empty for all): ").strip()
    if not raw:
        return options
    parts = raw.replace(",", " ").split()
    try:
        idxs = [int(p) - 1 for p in parts]
        return [options[i] for i in idxs if 0 <= i < len(options)]
    except ValueError:
        print("Invalid input. Please enter numbers separated by commas or spaces.")
        return choose_from_list(prompt, options)


def get_teams_from_csv(path: Path):
    df = pd.read_csv(path)
    df.columns = df.columns.str.lower().str.strip()
    if "home team" in df.columns and "away team" in df.columns:
        return set(df["home team"]).union(set(df["away team"]))
    else:
        raise ValueError(
            f"CSV {path} does not have expected 'Home Team'/'Away Team' columns. "
            f"Found: {df.columns.tolist()}"
        )


def make_canonical_mapper(selected_teams, threshold=86):
    """
    Returns a function that maps any team name to the best-matching selected team
    using fuzzy match; if no good match, returns the original name.
    """
    selected_teams = list(selected_teams)

    def _canon(name: str) -> str:
        if not selected_teams or not isinstance(name, str) or not name.strip():
            return name
        # token_set_ratio handles reordering & extra tokens like "FC", "CF"
        match = process.extractOne(name, selected_teams, scorer=fuzz.token_set_ratio)
        if match:
            best_name, score, _ = match
            if score >= threshold:
                return best_name
        return name

    return _canon


def main():
    data_dir = Path("data")
    files = sorted([f for f in data_dir.glob("*.csv")], key=lambda p: p.name.lower())
    if not files:
        print("❌ No CSV files found in data directory.")
        return

    # 1) Choose leagues (files)
    selected_files = choose_from_list("Select leagues:", [f.name for f in files])
    selected_paths = [data_dir / name for name in selected_files]

    # 2) Collect all teams across selected leagues
    all_teams = set()
    for path in selected_paths:
        all_teams |= get_teams_from_csv(path)

    # 3) Choose teams
    all_teams = sorted(all_teams)
    selected_teams = choose_from_list("Select teams:", all_teams)
    if not selected_teams:
        print("⚠️ No teams selected; nothing to export.")
        return

    # Build the fuzzy canonical mapper once
    canonicalize = make_canonical_mapper(selected_teams, threshold=86)

    # 4) Filter each league CSV and export an .ics per league
    total_events = 0
    for path in selected_paths:
        df = pd.read_csv(path)
        df.columns = df.columns.str.lower().str.strip()

        # Required columns check
        required_cols = {"date", "home team", "away team"}
        if not required_cols.issubset(df.columns):
            print(f"⏭️  Skipped {path.name}: missing one of {required_cols}. Found: {list(df.columns)}")
            continue

        # Parse dates (dayfirst=True to match your CSVs)
        df["date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=True)
        df = df.dropna(subset=["date"])

        # ---- Fuzzy-normalize team names to selected teams BEFORE filtering ----
        df["home team canon"] = df["home team"].apply(canonicalize)
        df["away team canon"] = df["away team"].apply(canonicalize)

        # Filter by selected teams using the canonicalized columns
        mask = df["home team canon"].isin(selected_teams) | df["away team canon"].isin(selected_teams)
        filtered = df[mask].copy()

        if filtered.empty:
            print(f"⏭️  No matches for selected teams in {path.name}.")
            continue

        # For nicer calendar titles, replace names with canonical ones in export
        filtered["home team"] = filtered["home team canon"]
        filtered["away team"] = filtered["away team canon"]
        filtered = filtered.drop(columns=["home team canon", "away team canon"], errors="ignore")

        # Add a competition/league label from the filename
        competition_label = path.stem  # e.g., 'la-liga-2025-UTC'
        ics_filename = f"{path.stem}.ics"

        export_to_ics(filtered, ics_filename, competition_name=competition_label)
        print(f"✅ Exported {len(filtered)} matches to {ics_filename}")
        total_events += len(filtered)

    if total_events == 0:
        print("⚠️ No matches exported. Check your selections or CSV contents.")
    else:
        print(f"🎉 Done. Exported {total_events} total matches across selected leagues.")


if __name__ == "__main__":
    main()