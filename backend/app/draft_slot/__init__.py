"""Draft-slot predictor research.

Uses historical NFL draft classes (players now in the league, plus combine invitees
who went undrafted) to measure which prospect traits are statistically associated
with where a player is selected. Findings feed feature design for the prospect /
player models under ``backend/app/ml``.

Entry point: ``python -m backend.app.draft_slot.cli``.
"""
