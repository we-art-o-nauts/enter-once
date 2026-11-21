# AI for Access - enter-once

Response to the Quartierzentrum Union challenge at [AI for Access - the Powercoders Hackathon](https://hackathon.powercoders.org). Developed by @loleg & agents - not an official project submission!

[Slide presentation](PRESENTATION.pdf) (auf Deutsch)

## The challenge

Quartierzentrum Union (Basel) runs its public activity programme from a single
**Outlook calendar**. Every event — from the centre itself, the bistro partner, or a
cooperation partner — is booked as a room reservation there.

Two websites must show this programme:

1. **union-basel.ch** (Webflow) — via an Elfsight calendar widget that is fed through a
   Google Calendar detour (Outlook → Google → Elfsight). The Webflow site itself stores
   no events.
2. **Verband Quartiertreffpunkt Basel** (WordPress) — via a custom-built event tool that is
   filled in **manually, one event at a time**.

Result: every event is captured a second time by hand. Typos, forgotten edits, cancelled
events that stay online — and the two sites drift apart.

The hackathon goal: **enter once in Outlook, publish everywhere — automatically.**

## The sprint (short version)

This sprint produced a working sync prototype (`union_sync.py`) that takes the ICS feed
from the Outlook test calendar and turns it into publishable event records:

- **In:** ICS source of truth (local sample `union-beispielkalender.ics` or the published
  Outlook test-calendar URL).
- **Processing:** parse VEVENTs → drop cancelled / internal / unmarked events → expand
  recurring series (`RRULE`: weekly, `UNTIL`, `COUNT`, `BYDAY`) → honour `EXDATE` skips and
  `RECURRENCE-ID` overrides (moved dates) → compute end times from the original duration.
- **Out:** human-readable event blocks or `--json` records ready for the websites, plus a
  sync state file that tracks published event IDs (for later deletion handling).

## The human-readable solution

The idea is simple: **Outlook stays the single source of truth.** The sync reads the
calendar, keeps only explicitly public events, and materialises them — one record per
concrete date for recurring series — into the format the target platforms consume.

- Cancelled events disappear.
- Internal room bookings (staff-only) never leave the calendar.
- Moved dates (`RECURRENCE-ID`) replace the original occurrence.
- Skipped dates (`EXDATE`) are not published.
- Recurring series become individual events (WordPress-style: one per date).

## Demo

```sh
./demo.sh
```

Runs the sync against the sample calendar and prints the published events.

## What a production deployment would need

- **Source:** the real Outlook ICS URL (or Microsoft Graph API for authenticated, reliable
  access) instead of the local sample file.
- **Webflow:** push events into the Webflow CMS via the CMS API (or replace the Elfsight
  widget with a custom event list fed by the sync output). Images, categories, tags and room
  references would be attached at publish time.
- **WordPress:** connect the custom event tool via ICS feed / Microsoft Graph / automation
  platform (Make/Zapier), or build the import into the tool itself; needs a publish/delete
  API for previously published events.
- **Public/internal marker:** a durable, staff-friendly convention (the current
  `CATEGORIES:Öffentlich` / `CLASS:PUBLIC` vs. `Intern` / `PRIVATE` split works for the
  sample; the real Outlook feed identifies public events only via Google Calendar
  invitations, which are not visible in ICS — a production marker must be agreed).
- **State & scheduling:** persistent store of published event IDs + scheduled sync runs
  (cron/serverless) for ongoing reconciliation and deletions.
- **Time handling:** `UNTIL` values are UTC; occurrences are timezone-aware (Europe/Berlin).
- **AI extension (future):** category typo correction (`Kulturr` → `Kultur`), missing
  descriptions, easy-language output, target-group assignment.

## Credits

- AI development assistant: [Flint](https://huggingface.co/RecursiveSI/flint) (by Recursive)
- Editor: [Zed](https://zed.dev)

License: [Apache 2.0](LICENSE)
