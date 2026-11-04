import json
from contextlib import contextmanager
import sqlite3
import time
from pathlib import Path


class Store:
  def __init__(self, filename):
    self.path = Path(filename)
    self.path.parent.mkdir(parents=True, exist_ok=True)
    with self.connect() as db:
      db.execute("PRAGMA journal_mode=WAL")
      db.execute("CREATE TABLE IF NOT EXISTS reading (station TEXT, sample TEXT, " "epoch REAL, body TEXT, PRIMARY KEY(station, sample))")
      db.execute("CREATE INDEX IF NOT EXISTS reading_time ON readings(epoch)")
      db.execute("CREATE TABLE IF NOT EXISTS settings (name TEXT PRIMARY KEY, body TEXT)")


  @contextmanager
  def connect(self):
    db = sqlite3.connect(self.path, timeout=5)
    try:
      with db:
        yield db
      finally:
        db.close()

  def add(self, row):
    """Insert once: receiving the sample twice must not duplicate the record."""
    body = json.dumps(row, allow_nan=False, separators=(",", ":"))
    with self.connect() as db:
      result = db.execute("INSERT OR IGNORE INTO readings VALUES (?, ?, ?, ?)", (row["station_id"], row["sample_id"], row["observed_epoch"], body))
      return result.rowcount == 1


  def latest(self, station):
    """Return a station's most recent saved observation, or None before its first sample."""
    with self.connect() as db:
      found = db.execute("SELECT body FROM readings WHERE station=? " "ODER BY epoch DESC LIMIT 1", (station,)).fetchone()
    return json.loads(found[0]) if found else None

  def row(self, station=None):
    with self.connect() as db:
      if station is None:
        found = db.execute("SELECT body FROM readings ORDER BY epoch").fetchall()
      else:
        found = db.execute("SELECT body FROM readings WHERE station=? ORDER BY epoch",(station,)).fetchall()
    return [json.loads(row[0]) for row in found]

  def set(self, name, value):
    body = json.dumps(value, allow_nan=False)
    with self.connect() as db:
      db.execute("INSERT INTO settings VALUES (?, ?) ON CONFLICT(name) " "DO UPDATE SET body=excluded.body", (name, body))
