# Independent Geodata Build Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `full`, `small`, and `internal` geodata variants from primary text sources owned by repository config instead of downloading upstream `.dat` artifacts.

**Architecture:** Add a Python-native geodata builder that downloads configured text sources, normalizes domain/IP entries, constructs category sets, subtracts blocked resources from `internal-*`, and emits V2Ray-compatible protobuf `.dat` files. Keep existing filter/extract scripts for compatibility, but make CI use the new builder and release layout.

**Tech Stack:** Python 3.11 standard library, pytest, GitHub Actions, raw V2Ray protobuf encoding helpers.

---

## File Structure

- Create: `config/sources.json`
  - Repository-owned source URL and variant configuration.
- Modify: `tools/geodat_proto.py`
  - Add protobuf encoders for GeoSite domain entries and GeoIP CIDR entries.
- Create: `tools/build_dat.py`
  - Main independent build pipeline.
- Create: `tests/test_build_dat.py`
  - Unit tests for source parsing, normalization, internal subtraction, and release layout.
- Modify: `.github/workflows/build.yml`
  - Replace upstream `.dat` download/filter steps with `tools/build_dat.py`.
- Modify: `README.md`
  - Document independent source build and root `internal` behavior.

---

### Task 1: Add protobuf encoders

**Files:**
- Modify: `tools/geodat_proto.py`
- Test: `tests/test_geodat_proto.py`

- [ ] Add tests for encoded geosite and geoip categories using existing `extract_categories`.
- [ ] Implement `encode_geosite_list(categories)`.
- [ ] Implement `encode_geoip_list(categories)`.
- [ ] Verify with `uvx pytest tests/test_geodat_proto.py -v`.

### Task 2: Add source config and builder core

**Files:**
- Create: `config/sources.json`
- Create: `tools/build_dat.py`
- Test: `tests/test_build_dat.py`

- [ ] Add config with source URLs and required category lists.
- [ ] Implement domain normalization.
- [ ] Implement CIDR normalization and exact CIDR subtraction.
- [ ] Implement parsers for plain domain/IP list formats and domain-list-community files.
- [ ] Implement variant construction for `full`, `small`, and `internal`.
- [ ] Verify with `uvx pytest tests/test_build_dat.py -v`.

### Task 3: Add release layout generation

**Files:**
- Modify: `tools/build_dat.py`
- Test: `tests/test_build_dat.py`

- [ ] Write `full/*`, `small/*`, `internal/*`.
- [ ] Copy internal files to root release paths.
- [ ] Generate category list files and sha256sum files for every variant.
- [ ] Validate root files match internal files.
- [ ] Verify with `uvx pytest tests/test_build_dat.py -v`.

### Task 4: Switch CI to independent build

**Files:**
- Modify: `.github/workflows/build.yml`

- [ ] Remove upstream `.dat` download and filter steps.
- [ ] Run `python3 tools/build_dat.py --config config/sources.json --output ./publish`.
- [ ] Validate all root/internal/small/full files are non-empty.
- [ ] Keep release upload and `release` branch force-push.
- [ ] Verify workflow YAML parses.

### Task 5: Update docs and final verification

**Files:**
- Modify: `README.md`

- [ ] Document root files as `internal`.
- [ ] Document `small/*` and `full/*` download paths.
- [ ] Run `uvx pytest -v`.
- [ ] Run `python3 -m py_compile tools/*.py tests/*.py`.
- [ ] Run YAML parse and `git diff --check`.

---

## Self-Review Notes

- Covers full/small/internal variants and root-as-internal release behavior.
- Keeps implementation bounded by using Python-native `.dat` generation for configured categories.
- First version supports exact CIDR subtraction; more advanced CIDR splitting can be added after real source analysis if needed.
