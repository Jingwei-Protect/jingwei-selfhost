"""Tests for tracking-anchor artist resolution on protect."""

from __future__ import annotations

from api.routes.protect import _resolve_track_artist


def test_resolve_track_artist_prefers_explicit_track_artist() -> None:
    got = _resolve_track_artist(
        track_artist="explicit",
        artist="artist",
        halftone_text="halftone",
    )
    assert got == "explicit"


def test_resolve_track_artist_falls_back_to_halftone_text() -> None:
    got = _resolve_track_artist(
        artist="",
        dwt_payload="",
        watermark_text="",
        signature_text="",
        halftone_text="jingwei",
    )
    assert got == "jingwei"


def test_resolve_track_artist_keeps_priority_before_halftone() -> None:
    got = _resolve_track_artist(
        artist="creator",
        halftone_text="jingwei",
    )
    assert got == "creator"
