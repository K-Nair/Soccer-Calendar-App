import pandas as pd
from models import Match
from rapidfuzz import fuzz, process


def normalize_team_name(name, team_list, threshold=85):
    """
    Normalize team names using fuzzy matching.
    - name: team name from CSV (e.g., "FC Barcelona")
    - team_list: list of canonical teams user selected
    - threshold: similarity % required to consider it the same
    """
    if not team_list:
        return name
    match, score, _ = process.extractOne(name, team_list, scorer=fuzz.token_sort_ratio)
    if score >= threshold:
        return match
    return name


def load_matches_from_csv(filename, selected_teams=None):
    df = pd.read_csv(filename)

    if selected_teams:
        # Normalize home/away names so they align with user selection
        df["home"] = df["home"].apply(lambda x: normalize_team_name(x, selected_teams))
        df["away"] = df["away"].apply(lambda x: normalize_team_name(x, selected_teams))

        # Keep only matches involving selected teams
        df = df[(df["home"].isin(selected_teams)) | (df["away"].isin(selected_teams))]

    matches = [
        Match(row["date"], row["home"], row["away"], row["competition"])
        for _, row in df.iterrows()
    ]
    return matches