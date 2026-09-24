"""Runtime feature flags.

Single source of truth for "is this optional capability turned on in this
deployment?". Read from environment variables so an Ops team can flip a
flag by editing a ConfigMap / Secret / .env and restarting the pod — no
code change needed.

Today there is exactly one flag (AI Insights). Add new flags here as
small dedicated functions so callers stay declarative:

    if features.ai_insights_enabled():
        ...
"""

from __future__ import annotations

import os


def _truthy(val: str | None) -> bool:
    return (val or "").strip().lower() in ("1", "true", "yes", "on")


def _falsy(val: str | None) -> bool:
    return (val or "").strip().lower() in ("0", "false", "no", "off")


def ai_insights_enabled() -> bool:
    """AI Insights (LLM-powered analytics on the Reports page).

    Tri-state on env var ``AI_INSIGHTS_ENABLED``:

    - ``true``  : force-on. The endpoint will run even if EMERGENT_LLM_KEY
                  is missing (and will fail loudly at request time, which
                  is what an Ops team wants when they're debugging).
    - ``false`` : force-off. The endpoint returns 503 and the admin UI
                  hides the AI Insights surface entirely. Use this for
                  air-gapped on-prem deployments that must not call out.
    - unset / "auto" (default) : auto-detect — enabled iff the
                  ``EMERGENT_LLM_KEY`` env var is non-empty.
    """
    raw = os.environ.get("AI_INSIGHTS_ENABLED")
    if _truthy(raw):
        return True
    if _falsy(raw):
        return False
    return bool(os.environ.get("EMERGENT_LLM_KEY", "").strip())


def attendant_mode_enabled() -> bool:
    """Parking-attendant flow.

    ``ATTENDANT_MODE_ENABLED`` (default ``true``):
    - ``true`` : on-site attendants confirm arrivals / report no-shows.
    - ``false``: site has no attendants. Parkers self-check-in via the app
                 within ``self_checkin_window_minutes()`` of their booked
                 start time; if they don't, the same background loop that
                 marks regular no-shows will also flip their reservation
                 to no-show, increment their counter, and (via the
                 existing release path + waitlist notifier) free the slot
                 for the next person.
    """
    raw = os.environ.get("ATTENDANT_MODE_ENABLED")
    if _falsy(raw):
        return False
    if _truthy(raw):
        return True
    return True  # default: attendant flow remains the historical default


def self_checkin_window_minutes() -> int:
    """Grace period (minutes) AFTER reservation ``start_time`` during which a
    parker can self-check-in. Outside that window the reservation flips to
    no-show. Only consulted when ``attendant_mode_enabled() is False``.

    Env var ``SELF_CHECKIN_WINDOW_MINUTES``; clamped to 5–240 to match the
    bounds we use elsewhere (no_show_release_minutes, waitlist_window).
    """
    raw = os.environ.get("SELF_CHECKIN_WINDOW_MINUTES", "15").strip()
    try:
        v = int(raw)
    except ValueError:
        v = 15
    return max(5, min(240, v))


def all_flags() -> dict:
    """Snapshot of every public flag, for the /api/system/features endpoint."""
    return {
        "ai_insights_enabled": ai_insights_enabled(),
        "attendant_mode_enabled": attendant_mode_enabled(),
        "self_checkin_window_minutes": self_checkin_window_minutes(),
    }
