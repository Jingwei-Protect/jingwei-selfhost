# Changelog

All notable changes to JWProtect Self-Hosted will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

This project has not yet made a tagged release; entries below are grouped
by date until the first version tag is cut.

## [Unreleased]

- Credit Quick on textured images now uses the small c024 displacement stamp
  only. A leftover ASCII checkbox or filled artist name no longer paints a
  full-screen letter grid.
- Credit Quick displacement is auto-placed on texture and cannot be dragged.
  On-image signature is independent of the creator name; empty signature
  falls back to the name only when sending.
- Auto placement searches the largest interior colour mass (the body), not
  the canvas centre, so surrounding flowers do not steal the stamp.
- Credit Quick stamp faintness is capped at the c024-on-fur depth, so a pin
  on busy flowers is no darker than the chest-fur stamp.

## 2026-09-06

- Aligned README wording with the attribution/verification positioning,
  added a C2PA scope note and disclaimer.

## 2026-09-02

- The GitHub Sponsor button now points to Ko-fi.

## 2026-08-30 — Initial public release

- First public self-hosted release: **Protect** and **Verify** workflows.
- Optional **AdvProtect** module (off by default; requires
  `requirements-adv.txt` and `ENABLE_ADV_PROTECT=1`).
- README documentation for Protect, Verify, and the visible-layer matrix.
- Credit Quick sample gallery with boxed/zoomed comparison crops.

[Unreleased]: [https://github.com/Jingwei-Protect/jingwei-selfhost/compare/84e8259...HEAD](https://github.com/Jingwei-Protect/jingwei-selfhost/compare/84e8259...HEAD)
