from pathlib import Path
import pandas as pd
import streamlit as st
from rapidfuzz import process, fuzz

from calendar_utils import calendar_text_from_df

DATA_DIR_DEFAULT = "data"

st.set_page_config(page_title="Soccer Calendar Builder", page_icon="⚽", layout="wide")
st.title("⚽ Soccer Calendar Builder")

# ---------------- League name cleaning ----------------

LEAGUE_NAME_MAP = {
    "bundesliga": "Bundesliga",
    "la-liga": "La Liga",
    "epl": "Premier League",
    "premier-league": "Premier League",
    "serie-a": "Serie A",
    "ligue-1": "Ligue 1",
    "ligue": "Ligue 1",  # fallback when "-1" gets stripped
    "eredivisie": "Eredivisie",
    "champions-league": "Champions League",
    "europa-league": "Europa League",
    "conference-league": "Conference League",
}

def clean_league_name(filename: str) -> str:
    """
    Turn a CSV filename like 'la-liga-2025-UTC.csv' into a pretty label like 'La Liga'.
    """
    stem = Path(filename).stem  # e.g., 'la-liga-2025-UTC'
    tokens = stem.split("-")

    # take tokens up to the first numeric token (e.g., '2025')
    prefix = []
    for t in tokens:
        if any(ch.isdigit() for ch in t):
            break
        prefix.append(t)

    # form candidate keys to look up in LEAGUE_NAME_MAP
    candidates = []
    if len(prefix) >= 2:
        candidates.append("-".join(prefix[:2]).lower())  # e.g., 'la-liga', 'europa-league'
    if prefix:
        candidates.append(prefix[0].lower())             # e.g., 'bundesliga', 'epl', 'ligue'
    # final fallback: just prettify the first token
    fallback = prefix[0].replace("-", " ").title() if prefix else stem.replace("-", " ").title()

    for key in candidates:
        if key in LEAGUE_NAME_MAP:
            return LEAGUE_NAME_MAP[key]
    return fallback

# ---------------- Sidebar: data location ----------------

st.sidebar.header("Data")
data_dir = st.sidebar.text_input("CSV folder", DATA_DIR_DEFAULT)
data_path = Path(data_dir)
if not data_path.exists():
    st.sidebar.error(f"Folder not found: {data_path.resolve()}")

# Load CSV files
csv_files = sorted([p for p in data_path.glob("*.csv")], key=lambda p: p.name.lower())
if not csv_files:
    st.info("Place your league CSV files in a folder (default: `data/`).")
    st.stop()

st.sidebar.write(f"Found **{len(csv_files)}** CSV files.")
st.sidebar.write("Tip: file names are used to infer pretty league names for calendar descriptions.")

# Select leagues (files)
league_names = [p.name for p in csv_files]
pretty_league_names = [clean_league_name(name) for name in league_names]
default_selection = league_names  # select all by default

selected_league_names = st.multiselect(
    "Choose leagues",
    options=league_names,
    default=default_selection,
    format_func=lambda fn: clean_league_name(fn),
)
selected_league_paths = [data_path / name for name in selected_league_names]

# ---------------- Helpers ----------------

def read_and_normalize(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = df.columns.str.lower().str.strip()  # normalize headers

    # require basic columns
    required = {"date", "home team", "away team"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path.name}: missing columns {missing}. Found: {list(df.columns)}")

    # parse date (your CSVs are dd/mm/YYYY HH:MM)
    df["date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=True)
    df = df.dropna(subset=["date"])

    # set a nice competition label (pretty name from filename) if not present
    if "competition" not in df.columns and "league" not in df.columns:
        df["competition"] = clean_league_name(path.name)

    return df

@st.cache_data(show_spinner=False)
def load_all_selected(paths: list[Path]) -> dict[str, pd.DataFrame]:
    out = {}
    for p in paths:
        out[p.name] = read_and_normalize(p)
    return out

def build_alias_clusters(team_names: list[str], threshold: int = 86):
    """
    Greedy clustering of aliases into canonical names (for ONE league).
    Returns (canonical_names, alias_to_canon).
    """
    protect_pairs = {
        ("Paris FC", "Paris Saint-Germain"),
        ("Paris", "Paris Saint-Germain"),
    }

    def protected(a: str, b: str) -> bool:
        return (a, b) in protect_pairs or (b, a) in protect_pairs

    canon_list: list[str] = []
    alias_to_canon: dict[str, str] = {}

    for name in sorted(team_names):
        if not canon_list:
            canon_list.append(name)
            alias_to_canon[name] = name
            continue

        best = process.extractOne(name, canon_list, scorer=fuzz.token_set_ratio)
        if best:
            best_name, score, _ = best
            if score >= threshold and not protected(name, best_name):
                alias_to_canon[name] = best_name
            else:
                canon_list.append(name)
                alias_to_canon[name] = name
        else:
            canon_list.append(name)
            alias_to_canon[name] = name

    canonical_names = sorted(set(alias_to_canon.values()))
    return canonical_names, alias_to_canon

def apply_canonical(df: pd.DataFrame, alias_to_canon: dict[str, str], selected_canon: set[str]) -> pd.DataFrame:
    """
    Map home/away to canonical names and filter rows by selected canonical teams.
    """
    df["home team canon"] = df["home team"].map(lambda x: alias_to_canon.get(x, x))
    df["away team canon"] = df["away team"].map(lambda x: alias_to_canon.get(x, x))
    mask = df["home team canon"].isin(selected_canon) | df["away team canon"].isin(selected_canon)
    filt = df[mask].copy()
    if not filt.empty:
        # show canonical names in the event title
        filt["home team"] = filt["home team canon"]
        filt["away team"] = filt["away team canon"]
        filt.drop(columns=["home team canon", "away team canon"], inplace=True, errors="ignore")
    return filt

# ---------------- Load data ----------------

try:
    league_dfs = load_all_selected(selected_league_paths)
except Exception as e:
    st.error(str(e))
    st.stop()

# ---------------- Team selection grouped by league ----------------

st.subheader("Select teams (grouped by league)")

threshold = st.slider("Alias grouping strength (handles 'FC Barcelona' ↔ 'Barcelona')", 70, 100, 86)

per_league_selected: dict[str, list[str]] = {}
per_league_alias_map: dict[str, dict[str, str]] = {}
per_league_canon_lists: dict[str, list[str]] = {}

for league_file, df in league_dfs.items():
    # derive display label: use competition column if single value, else pretty name from filename
    display_label = clean_league_name(league_file)
    label_col = "competition" if "competition" in df.columns else ("league" if "league" in df.columns else None)
    if label_col:
        uniq = df[label_col].dropna().unique()
        if len(uniq) == 1:
            display_label = str(uniq[0])

    team_names = sorted(set(df["home team"]) | set(df["away team"]))
    canon_names, alias_map = build_alias_clusters(team_names, threshold=threshold)
    per_league_alias_map[league_file] = alias_map
    per_league_canon_lists[league_file] = canon_names

    with st.expander(f"🏆 {display_label}", expanded=False):
        colA, colB = st.columns([3, 1])
        with colB:
            select_all = st.checkbox("Select all", key=f"selall_{league_file}")
        default_list = canon_names if select_all else []
        chosen = colA.multiselect(
            "Teams",
            options=canon_names,
            default=default_list,
            key=f"ms_{league_file}",
        )
        per_league_selected[league_file] = chosen

# Union of all chosen canonical teams across leagues
selected_canon_global: set[str] = set()
for chosen in per_league_selected.values():
    selected_canon_global.update(chosen)

# ---------------- Preview & export ----------------

if st.button("Preview matches"):
    if not selected_canon_global:
        st.warning("Pick at least one team in any league.")
        st.stop()

    filtered_frames = []
    for league_file, df in league_dfs.items():
        alias_map = per_league_alias_map.get(league_file, {})
        filt = apply_canonical(df.copy(), alias_map, selected_canon_global)
        if not filt.empty:
            # Ensure a label column exists for nicer .ics descriptions
            if "competition" not in filt.columns and "league" not in filt.columns:
                filt["competition"] = clean_league_name(league_file)
            filtered_frames.append(filt)

    if not filtered_frames:
        st.info("No matches found for your selection in the chosen leagues.")
        st.stop()

    combined = pd.concat(filtered_frames, ignore_index=True)
    combined.sort_values("date", inplace=True)

    st.subheader("Preview")
    label_col = "competition" if "competition" in combined.columns else "league"
    st.dataframe(
        combined[["date", "home team", "away team", label_col]],
        use_container_width=True,
    )

    st.subheader("Export")
    col1, col2 = st.columns(2)

    # A) Single combined .ics
    with col1:
        ics_text = calendar_text_from_df(combined, competition_name=None)
        st.download_button(
            label="Download combined calendar (my_teams.ics)",
            data=ics_text,
            file_name="my_teams.ics",
            mime="text/calendar",
        )

    # B) Per-league .ics
    with col2:
        per_league_files = {}
        for comp, group in combined.groupby(label_col):
            per_league_files[f"{comp}.ics"] = calendar_text_from_df(group, competition_name=str(comp))

        if per_league_files:
            pick = st.selectbox("Download per-league:", list(per_league_files.keys()))
            st.download_button(
                label="Download selected league",
                data=per_league_files[pick],
                file_name=pick,
                mime="text/calendar",
            )

st.caption("Teams are grouped by league with clean headers (e.g., 'La Liga'). Alias clustering collapses duplicates per league.")
