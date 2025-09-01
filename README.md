# Soccer Calendar App

A Python + Streamlit app that lets you:
- Select teams from multiple soccer leagues (CSV fixture data).
- Handles duplicate team names (e.g., `FC Barcelona` vs `Barcelona`) with fuzzy matching.
- Group teams by league for easy selection.
- Export fixtures to your personal calendar (`.ics` format), either combined or per-league.

---

## Features
- **Streamlit GUI** — easy-to-use web interface.
- **League grouping** — pick teams under each league.
- **Fuzzy matching** — merges aliases (`PSG` vs `Paris Saint-Germain`).
- **Calendar export** — download as `.ics` and import into Google Calendar, Apple Calendar, Outlook, etc.
- **Multiple outputs** — combined calendar or per-league calendars.

---

## Project Structure
```
  SoccerAPI/
    │── data/ # CSV fixture files (per league, e.g. la-liga-2025-UTC.csv)
    │── gui_app.py # Streamlit GUI app
    │── main.py # CLI version (optional)
    │── calendar_utils.py # Calendar export functions
    │── models.py # Match object (for CLI version)
    │── db.py # CSV loader & helper (for CLI version)
    │── requirements.txt # Python dependencies
    │── .gitignore # Ignore unneeded files
    │── README.md # Project description
    │── LICENSE # License file
```
---

## Installation

1. Clone the repo:
   ```bash
   git clone https://github.com/yourusername/soccer-calendar-app.git
   cd soccer-calendar-app
2. Create a virtual environment:
    ```bash
    python -m venv .venv
    source .venv/bin/activate   # Windows: .venv\Scripts\activate
    ```
3. Install dependencies:
   ```bash
    pip install -r requirements.txt


## Usage

1. Start the GUI
    ```bash
    streamlit run gui_app.py
    ```

   - Choose your leagues
   - Pick teams under each league
   - Preview fixtures
   - Export .ics files
3. CSV Data
      - Place your fixture CSVs in the data/ folder.
      - Expected format:
        - Date, Home Team, Away Team, Result
        24/08/2025 20:00, FC Barcelona, Real Madrid, 2 - 1

---


## Calendar Export
  - The app generates .ics files:
     - my_teams.ics → combined calendar with all selected teams.
     - <league-name>.ics → per-league calendars.
- Compatible with:
    - Apple Calendar
    - Google Calendar
    - Outlook
    - Any .ics compatible app

---


## Future Improvements:
  - Save user preferences (selected leagues/teams).
  - Add live API integration.
  - Deploy to Streamlit Cloud.
