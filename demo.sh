#!/bin/sh
# Hackathon demo runner for union_sync.py — runs the sync against the sample calendar.
cd "$(dirname "$0")"
.venv/bin/python union_sync.py --ics union-kit_kalender-cms-anleitung/union-beispielkalender.ics
