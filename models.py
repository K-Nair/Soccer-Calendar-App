from dataclasses import dataclass
from datetime import datetime

@dataclass
class Match:
    league: str
    date: datetime
    home: str
    away: str

    def __str__(self):
        return f"{self.date.strftime('%Y-%m-%d %H:%M')} - {self.home} vs {self.away} ({self.league})"