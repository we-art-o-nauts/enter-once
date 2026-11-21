#!/usr/bin/env python3
"""union_sync.py — Quartierzentrum Union: Outlook ICS -> Events für die Websites."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from icalendar import Calendar
from dateutil.rrule import rrule, WEEKLY, MONTHLY, DAILY, HOURLY, MINUTELY, SECONDLY, MO, TU, WE, TH, FR, SA, SU

FREQ_MAP = {"YEARLY": 3, "MONTHLY": 4, "WEEKLY": WEEKLY, "DAILY": DAILY, "HOURLY": HOURLY, "MINUTELY": MINUTELY, "SECONDLY": SECONDLY}

STATE_FILE = Path(".union_sync_state.json")
WD = {"MO": MO, "TU": TU, "WE": WE, "TH": TH, "FR": FR, "SA": SA, "SU": SU}


@dataclass
class Event:
    uid: str = ""
    summary: str = ""
    description: str = ""
    location: str = ""
    categories: list = field(default_factory=list)
    klass: str = ""
    status: str = ""
    sequence: int = 0
    dtstart: datetime = None
    dtend: datetime = None
    rrule: dict = None
    exdates: list = field(default_factory=list)
    recurrence_id: datetime = None


def to_utc(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc)


def _parse_rrule(rr) -> dict:
    data = {}
    if rr is None:
        return None
    for key in ("FREQ", "UNTIL", "COUNT", "BYDAY", "INTERVAL"):
        try:
            val = rr[key]
        except Exception:
            continue
        if isinstance(val, list):
            val = val[0] if val else None
        if key == "FREQ":
            data[key] = FREQ_MAP.get(str(val), WEEKLY)
        else:
            data[key] = val
    return data


def parse_ics(text: str) -> list:
    cal = Calendar.from_ical(text)
    events = []
    for component in cal.walk("VEVENT"):
        ev = Event()
        ev.uid = str(component.get("UID") or "")
        ev.summary = str(component.get("SUMMARY") or "")
        ev.description = str(component.get("DESCRIPTION") or "")
        ev.location = str(component.get("LOCATION") or "")
        cats = component.get("CATEGORIES")
        ev.categories = [str(x) for x in cats] if cats is not None else []
        ev.klass = str(component.get("CLASS") or "").upper()
        ev.status = str(component.get("STATUS") or "").upper()
        seq = component.get("SEQUENCE")
        ev.sequence = int(seq) if seq is not None else 0
        ev.dtstart = component.get("DTSTART").dt if component.get("DTSTART") else None
        end = component.get("DTEND")
        ev.dtend = end.dt if end is not None else None
        ev.rrule = _parse_rrule(component.get("RRULE"))
        ex = component.get("EXDATE")
        ev.exdates = []
        if ex is not None:
            exlist = ex if isinstance(ex, list) else [ex]
            for lst in exlist:
                for d in lst.dts:
                    ev.exdates.append(d.dt)
        rid = component.get("RECURRENCE-ID")
        ev.recurrence_id = rid.dt if rid is not None else None
        events.append(ev)
    return events


# ---------- filtering & recurrence ----------

def should_publish(ev: Event) -> bool:
    if ev.status == "CANCELLED":
        return False
    cats = " ".join(ev.categories)
    if "Intern" in cats or ev.klass == "PRIVATE":
        return False
    if "Öffentlich" in cats or ev.klass == "PUBLIC":
        return True
    # Unmarked events are deliberately NOT published (safe default).
    return False


def generate_occurrences(ev: Event) -> list:
    if ev.rrule is None or ev.rrule.get("FREQ") is None:
        return [ev.dtstart] if ev.dtstart else []
    kw = {
        "freq": FREQ_MAP.get(str(ev.rrule.get("FREQ") or "WEEKLY"), WEEKLY),
        "dtstart": ev.dtstart,
        "interval": int(ev.rrule.get("INTERVAL") or 1),
    }
    if ev.rrule.get("BYDAY"):
        names = [str(d).strip().upper() for d in str(ev.rrule["BYDAY"]).split(",")]
        byweekday = [WD[n] for n in names if n in WD]
        if byweekday:
            kw["byweekday"] = byweekday
    if ev.rrule.get("UNTIL"):
        kw["until"] = ev.rrule["UNTIL"]
    if ev.rrule.get("COUNT"):
        kw["count"] = int(ev.rrule["COUNT"])
    occs = list(rrule(**kw))
    out = []
    for o in occs:
        if any(to_utc(o) == to_utc(e) for e in ev.exdates):
            continue
        out.append(o)
    return out


def build_records(events: list, from_dt=None, to_dt=None):
    records = []
    for ev in events:
        if not should_publish(ev):
            continue
        if ev.recurrence_id is not None:
            records.append((ev, ev.dtstart))
            continue
        starts = generate_occurrences(ev)
        override_starts = set()
        for other in events:
            if other.uid == ev.uid and other.recurrence_id is not None:
                override_starts.add(to_utc(other.recurrence_id))
        for s in starts:
            if to_utc(s) in override_starts:
                continue
            if from_dt and s < from_dt:
                continue
            if to_dt and s > to_dt:
                continue
            records.append((ev, s))
    records.sort(key=lambda r: r[1])
    return records


def to_record(ev: Event, start: datetime) -> dict:
    duration = (ev.dtend - ev.dtstart).total_seconds() if ev.dtend and ev.dtstart else 3600.0
    end = start + timedelta(seconds=duration)
    cats, tags = parse_sections(ev.description)
    room = ev.location.split(",")[0].strip() if ev.location else ""
    image = ev.summary.strip().replace(" ", "_") + ".jpg"
    return {
        "uid": ev.uid,
        "summary": ev.summary,
        "description": ev.description,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "room": room,
        "categories": cats,
        "tags": tags,
        "image": image,
        "status": ev.status,
        "sequence": ev.sequence,
        "public": True,
    }


def parse_sections(description: str):
    def grab(block_name: str):
        pattern = r"\[" + block_name + r"\](.*?)\[/" + block_name + r"\]"
        blocks = re.findall(pattern, description, re.S)
        names = []
        for b in blocks:
            names += [n.strip() for n in re.findall(r"name=(.*)", b) if n.strip()]
        return names

    return grab("event-type"), grab("tag")


# ---------- state & deletions ----------

def load_state(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(path: Path, records) -> None:
    state = {to_record(ev, start)["uid"]: to_record(ev, start) for ev, start in records}
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------- CLI ----------

def fetch_ics(url: str) -> str:
    import urllib.request
    with urllib.request.urlopen(url, timeout=15) as resp:
        return resp.read().decode("utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Union ICS -> publishable events")
    ap.add_argument("--ics", default="union-kit_kalender-cms-anleitung/union-beispielkalender.ics", help="Path to local .ics file")
    ap.add_argument("--calendar", default=None, help="ICS URL (e.g. Outlook test calendar)")
    ap.add_argument("--json", action="store_true", help="Output JSON")
    ap.add_argument("--from", dest="from_dt", default=None, help="Window start (YYYY-MM-DD)")
    ap.add_argument("--to", dest="to_dt", default=None, help="Window end (YYYY-MM-DD)")
    ap.add_argument("--state", default=str(STATE_FILE), help="Path to sync-state JSON file")
    args = ap.parse_args(argv)

    if args.calendar:
        text = fetch_ics(args.calendar)
        source = args.calendar
    else:
        source = args.ics
        text = open(args.ics, encoding="utf-8").read()

    events = parse_ics(text)
    from_dt = datetime.fromisoformat(args.from_dt) if args.from_dt else None
    to_dt = datetime.fromisoformat(args.to_dt) if args.to_dt else None
    if to_dt:
        to_dt = to_dt.replace(hour=23, minute=59, second=59)

    state_path = Path(args.state)
    prev = load_state(state_path)
    records = build_records(events, from_dt=from_dt, to_dt=to_dt)
    current_uids = {r[0].uid for r in records}
    deletions = [uid for uid in prev if uid not in current_uids]

    if args.json:
        out = [to_record(ev, start) for ev, start in records]
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(f"📡 Quelle: {source}")
        print(f"📦 Events gelesen: {len(events)} | ⏭️  Veröffentlicht: {len(records)} | 🗑️  Gelöscht (Sync): {len(deletions)}")
        for uid in deletions:
            print(f"   🗑️  Wird gelöscht (war zuvor veröffentlicht): {uid}")
        for ev, start in records:
            rec = to_record(ev, start)
            cats, tags = parse_sections(ev.description)
            cat_str = " · ".join(cats) if cats else "(keine Kategorie — AI-Fall)"
            tag_str = ", ".join(tags) if tags else ""
            print(f"\n✅ {rec['summary']}")
            print(f"   📅 {start.strftime('%a %d.%m.%Y, %H:%M')} – {rec['end'][11:16]} Uhr")
            print(f"   📍 {rec['room']}")
            print(f"   🏷️  Kategorie: {cat_str}")
            if tag_str:
                print(f"   🏷️  Tags: {tag_str}")
            print(f"   📝 {ev.description.split(chr(10) + chr(10))[0].strip()}")
            print(f"   🖼️  {rec['image']}")
            if ev.rrule:
                print(f"   🔁 Serie: wöchentlich (BYDAY={ev.rrule.get('BYDAY')}), SEQUENCE={ev.sequence}")

    save_state(state_path, records)
    return 0


if __name__ == "__main__":
    sys.exit(main())
