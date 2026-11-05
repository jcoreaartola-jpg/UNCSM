import sqlite3
from pathlib import Path
DB = Path(__file__).with_name('torneo.db')

def connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS teams(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL);
        CREATE TABLE IF NOT EXISTS matches(
          id INTEGER PRIMARY KEY, phase TEXT NOT NULL, round_no INTEGER DEFAULT 0,
          leg INTEGER DEFAULT 1, home_id INTEGER NOT NULL, away_id INTEGER NOT NULL,
          hg INTEGER, ag INTEGER, hp INTEGER, ap INTEGER, played INTEGER DEFAULT 0,
          FOREIGN KEY(home_id) REFERENCES teams(id), FOREIGN KEY(away_id) REFERENCES teams(id));
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        INSERT OR IGNORE INTO settings(key,value) VALUES('calendar','0');
        ''')
