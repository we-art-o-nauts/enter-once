# AGENTS.md — enter-once / Quartierzentrum Union

## Project purpose

Hackathon solution (`AI for Access Hackathon`, 20.–21. November 2026) for
**Quartierzentrum Union** (Basel): events are managed once in an **Outlook calendar**
and must automatically appear on two websites:

1. **union-basel.ch** (Webflow; own site) — today via Elfsight widget fed through a
   Google Calendar detour (Outlook → Google via custom script → Elfsight).
2. **Verband Quartiertreffpunkt Basel** (WordPress; umbrella association for 16
   neighbourhood centres) — today via a custom-built, manually-filled event tool.

The challenge: avoid double entry on the WordPress side; apply changes/cancellations
automatically; publish only public events.

## Goals / success criteria

- **Minimum (Option B):** no manual entry on WordPress; changes & cancellations sync
  automatically; easy to use without technical background.
- **Ideal (Option A):** one entry in Outlook → automatically on both sites; transferable
  to other neighbourhood centres.
- **Optional AI:** easy-language event descriptions; automatic category / target-group
  assignment.

## Current implementation state

- `union_sync.py` — CLI prototype (Python stdlib, now migrating to `icalendar` +
  `python-dateutil` via `uv`).
- `src/enter_once/__init__.py` — package stub (`main()` prints "Hello from enter-once!").
  The real logic currently lives in the root-level `union_sync.py`; wiring into the
  package console script (`enter-once = "enter_once:main"`) is still pending.

### Pipeline (union_sync.py)

1. Read ICS (local sample file or Outlook test-calendar URL).
2. Parse VEVENTs via `icalendar.Calendar.from_ical`.
3. Filter: skip `STATUS:CANCELLED`; skip internal (`CATEGORIES:Intern` / `CLASS:PRIVATE`);
   publish **only explicitly public** events (`CATEGORIES:Öffentlich` / `CLASS:PUBLIC`).
4. Expand recurrences via `dateutil.rrule` (WEEKLY; `UNTIL`, `COUNT`, `BYDAY`), honour
   `EXDATE` (skipped dates) and `RECURRENCE-ID` (moved/edited instances → override).
5. Build publishable records: start/end (end = occurrence start + original duration),
   room, categories, tags, description, image (title with spaces → `_`), sequence.
6. Output: human-readable CLI print or `--json`.
7. Sync state: persistent event IDs + deletion handling (previously published events that
   no longer exist must be removed).

## ICS data contract (Union conventions)

- `SUMMARY` — official event name; also image key (title, spaces → `_`, e.g. `Offener_Deutschtreff.jpg`).
- `LOCATION` — room name (plus optional address suffix).
- `DESCRIPTION` — event text, then `[event-type]` block(s) with `name=…`, then `[tag]` blocks.
- `CATEGORIES` — `Öffentlich` / `Intern` (public marker convention; real Outlook feed uses
  `CLASS:PUBLIC`).
- `CLASS`, `STATUS`, `SEQUENCE` — `PUBLIC`/`PRIVATE`, `CONFIRMED`/`CANCELLED`, version.
- `RRULE`, `EXDATE`, `RECURRENCE-ID` — recurrence / skips / overrides.

Known edge cases in sample (`union-kit_kalender-cms-anleitung/union-beispielkalender.ics`):
skipped dates (`EXDATE`), moved date (`RECURRENCE-ID`), cancellation (`STATUS:CANCELLED`),
typo in category (`Kulturr`), missing description (AI case), internal bookings.

## Tech stack / commands

- Python >= 3.12, managed with **uv** (`uv.lock`, `.venv`).
- Dependencies: `icalendar>=7.3.2`, `python-dateutil>=4.0.0`.
- Run: `uv run union_sync.py --ics union-kit_kalender-cms-anleitung/union-beispielkalender.ics`
  (or `.venv/bin/python union_sync.py ...`).

## Open work / next steps

- Finish migration of `union_sync.py` logic into `src/enter_once` package + console script.
- Add sync-state file & deletion handling for WordPress publish/delete.
- Connect to Webflow CMS / WordPress event tool (staging/sandbox, no live access).
- AI extension: category correction (`Kulturr` → `Kultur`), missing categories, easy language.
- Demo script for the 30-minute hackathon slot.
