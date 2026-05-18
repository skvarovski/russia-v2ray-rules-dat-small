# Hardening Geodata Build Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the small geodata build pipeline safer, less duplicated, and better documented.

**Architecture:** Extract duplicated protobuf helpers into one local module, cover parser/filter behavior with small generated binary fixtures, then harden GitHub Actions so invalid downloads or missing categories stop publication. Keep the existing no-dependency runtime model for the tools.

**Tech Stack:** Python 3.11 standard library, pytest for tests, GitHub Actions, shell utilities (`curl`, `test`, `sha256sum`).

---

## File Structure

- Create: `tools/geodat_proto.py`
  - Shared no-dependency protobuf varint helpers, top-level entry parser, category extraction, and category-list writer.
- Modify: `tools/filter-geosite.py`
  - Keep geosite default category list and CLI, delegate parsing/encoding to `tools/geodat_proto.py`.
- Modify: `tools/filter-geoip.py`
  - Keep geoip default category list and CLI, delegate parsing/encoding to `tools/geodat_proto.py`.
- Modify: `tools/extract-categories.py`
  - Delegate category extraction and output writing to `tools/geodat_proto.py`.
- Create: `tests/test_geodat_proto.py`
  - Unit tests for varint handling, category extraction, malformed protobuf data, and full filter round trip with generated fixtures.
- Create: `tests/test_tools_cli.py`
  - CLI-level tests for filter scripts and category extraction script.
- Create: `pytest.ini`
  - Configure pytest discovery and add repository root to `pythonpath`.
- Modify: `.github/workflows/build.yml`
  - Add token permissions, strict shell behavior, failing download checks, generated-file validation, and required-category validation.
- Modify: `README.md`
  - Clarify that this repository publishes a reduced category set, document actual default categories, and fix download links if repository name differs from upstream.

---

### Task 1: Add Test Harness and Binary Fixture Helpers

**Files:**
- Create: `pytest.ini`
- Create: `tests/test_geodat_proto.py`

- [ ] **Step 1: Add pytest configuration**

Create `pytest.ini`:

```ini
[pytest]
pythonpath = .
testpaths = tests
```

- [ ] **Step 2: Add fixture helpers with expected protobuf shape**

Create `tests/test_geodat_proto.py` with fixture builders that encode a minimal `GeoSiteList`/`GeoIPList` equivalent:

```python
from tools.geodat_proto import encode_field_len, encode_varint


def make_entry(category: str, payload_field: int = 2, payload: bytes = b"x") -> bytes:
    inner = encode_field_len(1, category.encode("utf-8"))
    inner += encode_field_len(payload_field, payload)
    return encode_field_len(1, inner)


def make_dat(*categories: str) -> bytes:
    return b"".join(make_entry(category) for category in categories)


def test_encode_varint_single_and_multi_byte_values():
    assert encode_varint(0) == b"\x00"
    assert encode_varint(127) == b"\x7f"
    assert encode_varint(128) == b"\x80\x01"
    assert encode_varint(300) == b"\xac\x02"
```

This test will initially fail because `tools.geodat_proto` does not exist.

- [ ] **Step 3: Run test to verify it fails**

Run:

```bash
pytest tests/test_geodat_proto.py::test_encode_varint_single_and_multi_byte_values -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'tools.geodat_proto'`.

- [ ] **Step 4: Commit**

```bash
git add pytest.ini tests/test_geodat_proto.py
git commit -m "test: add geodat parser test harness"
```

---

### Task 2: Extract Shared Protobuf Helpers

**Files:**
- Create: `tools/geodat_proto.py`
- Modify: `tests/test_geodat_proto.py`

- [ ] **Step 1: Implement shared helper module**

Create `tools/geodat_proto.py`:

```python
import os


class ProtoParseError(ValueError):
    """Raised when a geodata protobuf file is truncated or malformed."""


def read_varint(data: bytes, pos: int) -> tuple[int, int]:
    result = 0
    shift = 0
    start = pos
    while True:
        if pos >= len(data):
            raise ProtoParseError(f"truncated varint at offset {start}")
        b = data[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, pos
        shift += 7
        if shift >= 64:
            raise ProtoParseError(f"varint too long at offset {start}")


def encode_varint(value: int) -> bytes:
    if value < 0:
        raise ValueError("varint value must be non-negative")
    buf = []
    while True:
        b = value & 0x7F
        value >>= 7
        if value:
            buf.append(b | 0x80)
        else:
            buf.append(b)
            break
    return bytes(buf)


def encode_field_len(field_number: int, payload: bytes) -> bytes:
    tag = (field_number << 3) | 2
    return encode_varint(tag) + encode_varint(len(payload)) + payload


def require_available(data: bytes, pos: int, length: int, context: str) -> None:
    if length < 0 or pos + length > len(data):
        raise ProtoParseError(f"truncated {context} at offset {pos}")


def skip_field(data: bytes, pos: int, wire: int) -> int:
    if wire == 0:
        _, pos = read_varint(data, pos)
        return pos
    if wire == 1:
        require_available(data, pos, 8, "64-bit field")
        return pos + 8
    if wire == 2:
        length, pos = read_varint(data, pos)
        require_available(data, pos, length, "length-delimited field")
        return pos + length
    if wire == 5:
        require_available(data, pos, 4, "32-bit field")
        return pos + 4
    raise ProtoParseError(f"unsupported wire type {wire} at offset {pos}")


def get_country_code(entry_data: bytes) -> str:
    pos = 0
    while pos < len(entry_data):
        tag_wire, pos = read_varint(entry_data, pos)
        field = tag_wire >> 3
        wire = tag_wire & 7
        if wire == 2:
            length, pos = read_varint(entry_data, pos)
            require_available(entry_data, pos, length, "country_code payload")
            payload = entry_data[pos:pos + length]
            pos += length
            if field == 1:
                return payload.decode("utf-8", errors="replace")
        else:
            pos = skip_field(entry_data, pos, wire)
    return ""


def parse_entries(data: bytes) -> list[tuple[str, bytes]]:
    entries = []
    pos = 0
    while pos < len(data):
        tag_wire, pos = read_varint(data, pos)
        field = tag_wire >> 3
        wire = tag_wire & 7
        if wire != 2:
            raise ProtoParseError(f"unexpected wire type {wire} for field {field} at offset {pos - 1}")
        length, pos = read_varint(data, pos)
        require_available(data, pos, length, "top-level entry")
        entry_data = data[pos:pos + length]
        pos += length
        if field == 1:
            entries.append((get_country_code(entry_data), entry_data))
    return entries


def extract_categories(data: bytes) -> list[str]:
    return sorted({code.upper() for code, _ in parse_entries(data) if code})


def write_categories_file(entries: list[tuple[str, bytes]], output_path: str) -> None:
    codes = sorted({code.upper() for code, _ in entries if code})
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(codes) + "\n")
    print(f"Categories file: {output_path} ({len(codes)} entries)")
```

- [ ] **Step 2: Add parser tests**

Append to `tests/test_geodat_proto.py`:

```python
import pytest

from tools.geodat_proto import ProtoParseError, extract_categories, parse_entries


def test_parse_entries_extracts_categories_and_preserves_inner_payload():
    data = make_dat("google", "RU-BLOCKED")

    entries = parse_entries(data)

    assert [code for code, _ in entries] == ["google", "RU-BLOCKED"]
    assert extract_categories(data) == ["GOOGLE", "RU-BLOCKED"]
    assert all(blob for _, blob in entries)


def test_parse_entries_rejects_truncated_length_delimited_field():
    data = encode_varint((1 << 3) | 2) + encode_varint(10) + b"abc"

    with pytest.raises(ProtoParseError, match="truncated top-level entry"):
        parse_entries(data)


def test_read_varint_rejects_truncated_varint():
    data = b"\x80"

    with pytest.raises(ProtoParseError, match="truncated varint"):
        parse_entries(data)
```

- [ ] **Step 3: Run tests**

Run:

```bash
pytest tests/test_geodat_proto.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add tools/geodat_proto.py tests/test_geodat_proto.py
git commit -m "feat: share geodat protobuf helpers"
```

---

### Task 3: Refactor Filter and Extract Scripts to Use Shared Module

**Files:**
- Modify: `tools/filter-geosite.py`
- Modify: `tools/filter-geoip.py`
- Modify: `tools/extract-categories.py`
- Modify: `tests/test_geodat_proto.py`
- Create: `tests/test_tools_cli.py`

- [ ] **Step 1: Add filtering helper tests**

Append to `tests/test_geodat_proto.py`:

```python
from tools.geodat_proto import encode_field_len


def test_filter_round_trip_can_rebuild_selected_entries():
    entries = parse_entries(make_dat("GOOGLE", "RU", "PRIVATE"))
    selected = [(code, blob) for code, blob in entries if code.upper() in {"GOOGLE", "PRIVATE"}]
    output = b"".join(encode_field_len(1, blob) for _, blob in selected)

    assert extract_categories(output) == ["GOOGLE", "PRIVATE"]
```

- [ ] **Step 2: Update `tools/filter-geosite.py` imports and remove duplicate helpers**

In `tools/filter-geosite.py`, replace local definitions of `read_varint`, `encode_varint`, `encode_field_len`, `get_country_code`, `parse_entries`, and `write_categories_file` with:

```python
from geodat_proto import encode_field_len, parse_entries, write_categories_file
```

Keep `DEFAULT_CATEGORIES` and `main()` behavior unchanged except file writes should remain binary for `.dat`.

- [ ] **Step 3: Update `tools/filter-geoip.py` imports and remove duplicate helpers**

In `tools/filter-geoip.py`, replace local definitions of `read_varint`, `encode_varint`, `encode_field_len`, `get_country_code`, `parse_entries`, and `write_categories_file` with:

```python
from geodat_proto import encode_field_len, parse_entries, write_categories_file
```

Keep `DEFAULT_CATEGORIES` and `main()` behavior unchanged.

- [ ] **Step 4: Update `tools/extract-categories.py` imports and remove duplicate parser**

In `tools/extract-categories.py`, replace local parser functions with:

```python
from geodat_proto import extract_categories
```

Keep the CLI signature:

```bash
python3 tools/extract-categories.py <geosite|geoip> <input.dat> <output.txt>
```

- [ ] **Step 5: Add CLI smoke tests**

Create `tests/test_tools_cli.py`:

```python
import subprocess
import sys

from tests.test_geodat_proto import make_dat
from tools.geodat_proto import extract_categories


def test_filter_geosite_cli_writes_filtered_dat_and_category_lists(tmp_path):
    source = tmp_path / "geosite.dat"
    output = tmp_path / "publish" / "geosite.dat"
    source.write_bytes(make_dat("GOOGLE", "RU-BLOCKED", "UNUSED"))

    result = subprocess.run(
        [sys.executable, "tools/filter-geosite.py", str(source), str(output), "GOOGLE", "RU-BLOCKED"],
        check=True,
        text=True,
        capture_output=True,
    )

    assert "Selected: 2 categories" in result.stdout
    assert extract_categories(output.read_bytes()) == ["GOOGLE", "RU-BLOCKED"]
    assert (tmp_path / "publish" / "geosite.txt").read_text(encoding="utf-8") == "GOOGLE\nRU-BLOCKED\n"
    assert "UNUSED\n" in (tmp_path / "publish" / "geosite_full.txt").read_text(encoding="utf-8")


def test_filter_geoip_cli_writes_filtered_dat(tmp_path):
    source = tmp_path / "geoip.dat"
    output = tmp_path / "publish" / "geoip.dat"
    source.write_bytes(make_dat("RU", "PRIVATE", "UNUSED"))

    subprocess.run(
        [sys.executable, "tools/filter-geoip.py", str(source), str(output), "RU", "PRIVATE"],
        check=True,
        text=True,
        capture_output=True,
    )

    assert extract_categories(output.read_bytes()) == ["PRIVATE", "RU"]


def test_extract_categories_cli_writes_sorted_uppercase_list(tmp_path):
    source = tmp_path / "geosite.dat"
    output = tmp_path / "categories.txt"
    source.write_bytes(make_dat("google", "RU-BLOCKED"))

    result = subprocess.run(
        [sys.executable, "tools/extract-categories.py", "geosite", str(source), str(output)],
        check=True,
        text=True,
        capture_output=True,
    )

    assert "geosite: 2 categories extracted" in result.stdout
    assert output.read_text(encoding="utf-8") == "GOOGLE\nRU-BLOCKED\n"
```

- [ ] **Step 6: Run all tests and compile scripts**

Run:

```bash
pytest -v
python3 -m py_compile tools/*.py
```

Expected: all tests PASS and compile exits 0.

- [ ] **Step 7: Commit**

```bash
git add tools/geodat_proto.py tools/filter-geosite.py tools/filter-geoip.py tools/extract-categories.py tests/test_geodat_proto.py tests/test_tools_cli.py
git commit -m "refactor: reuse geodat protobuf parser"
```

---

### Task 4: Harden Workflow Downloads and Publication Gates

**Files:**
- Modify: `.github/workflows/build.yml`

- [ ] **Step 1: Add workflow permissions and strict shell defaults**

Add near the top of `.github/workflows/build.yml`:

```yaml
permissions:
  contents: write

defaults:
  run:
    shell: bash
```

- [ ] **Step 2: Replace download step with failing download checks**

Replace the `Download geodata` step body with:

```yaml
      - name: Download geodata
        run: |
          set -euo pipefail
          mkdir -p ./publish
          curl -fL --retry 3 --retry-delay 5 "$GEOIP_URL" -o ./full-geoip.dat
          curl -fL --retry 3 --retry-delay 5 "$GEOSITE_URL" -o ./full-geosite.dat
          test -s ./full-geoip.dat
          test -s ./full-geosite.dat
```

- [ ] **Step 3: Add required category validation after filtering**

Add this step after `Generate category lists`:

```yaml
      - name: Validate generated assets
        run: |
          set -euo pipefail
          test -s ./publish/geosite.dat
          test -s ./publish/geoip.dat
          test -s ./publish/geosite_categories.txt
          test -s ./publish/geoip_categories.txt

          required_geosite=(
            RU-BLOCKED
            ANTIFILTER-DOWNLOAD-COMMUNITY
            CATEGORY-MEDIA
            CATEGORY-COMMUNICATION
            CATEGORY-SOCIAL-MEDIA-!CN
            CATEGORY-ENTERTAINMENT
            CATEGORY-GAMES
            CATEGORY-DEV
            CATEGORY-FORUMS
            CATEGORY-AI-!CN
            CATEGORY-ANTICENSORSHIP
            CATEGORY-VPNSERVICES
            CATEGORY-CRYPTOCURRENCY
            CATEGORY-SCHOLAR-!CN
            CATEGORY-CDN-!CN
            GOOGLE
            CLOUDFLARE
            AMAZON
            CATEGORY-RU
            RU-AVAILABLE-ONLY-INSIDE
            CATEGORY-BANK-RU
            CATEGORY-GOV-RU
            PRIVATE
            CATEGORY-ADS-ALL
          )

          required_geoip=(
            RU-BLOCKED
            RE-FILTER
            RU-BLOCKED-COMMUNITY
            TELEGRAM
            GOOGLE
            CLOUDFLARE
            RU
            RU-WHITELIST
            YANDEX
            DDOS-GUARD
            PRIVATE
          )

          for category in "${required_geosite[@]}"; do
            grep -Fx "$category" ./publish/geosite_categories.txt >/dev/null
          done

          for category in "${required_geoip[@]}"; do
            grep -Fx "$category" ./publish/geoip_categories.txt >/dev/null
          done
```

- [ ] **Step 4: Add local syntax check for workflow-adjacent Python**

Add this step before downloads:

```yaml
      - name: Check Python tools
        run: |
          set -euo pipefail
          python3 -m py_compile tools/*.py
```

- [ ] **Step 5: Verify workflow YAML parses**

Run:

```bash
python3 - <<'PY'
import pathlib
import yaml
path = pathlib.Path(".github/workflows/build.yml")
yaml.safe_load(path.read_text())
print("workflow yaml ok")
PY
```

If `PyYAML` is unavailable locally, run:

```bash
ruby -e 'require "yaml"; YAML.load_file(".github/workflows/build.yml"); puts "workflow yaml ok"'
```

Expected: prints `workflow yaml ok`.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/build.yml
git commit -m "ci: harden geodata publication pipeline"
```

---

### Task 5: Align README With the Small Filtered Dataset

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Change project description**

Update the first section to state that this repository publishes a reduced subset of the upstream Russian V2Ray geodata files:

```markdown
# Что это?

Этот репозиторий содержит автоматически обновляемую уменьшенную сборку `geoip.dat` и `geosite.dat` для V2Ray-совместимых клиентов. Файлы собираются из upstream-источников runetfreedom и содержат только категории, перечисленные ниже.
```

- [ ] **Step 2: Document actual `geoip.dat` categories**

Replace the broad `geoip.dat` category description with the exact default categories from `tools/filter-geoip.py`:

```markdown
### geoip.dat

В уменьшенную сборку включены:

- `geoip:ru-blocked`
- `geoip:re-filter`
- `geoip:ru-blocked-community`
- `geoip:telegram`
- `geoip:google`
- `geoip:cloudflare`
- `geoip:ru`
- `geoip:ru-whitelist`
- `geoip:yandex`
- `geoip:ddos-guard`
- `geoip:private`
```

- [ ] **Step 3: Document actual `geosite.dat` categories**

Replace the broad `geosite.dat` category description with the exact default categories from `tools/filter-geosite.py`:

```markdown
### geosite.dat

В уменьшенную сборку включены:

- `geosite:ru-blocked`
- `geosite:antifilter-download-community`
- `geosite:category-media`
- `geosite:category-communication`
- `geosite:category-social-media-!cn`
- `geosite:category-entertainment`
- `geosite:category-games`
- `geosite:category-dev`
- `geosite:category-forums`
- `geosite:category-ai-!cn`
- `geosite:category-anticensorship`
- `geosite:category-vpnservices`
- `geosite:category-cryptocurrency`
- `geosite:category-scholar-!cn`
- `geosite:category-cdn-!cn`
- `geosite:google`
- `geosite:cloudflare`
- `geosite:amazon`
- `geosite:category-ru`
- `geosite:ru-available-only-inside`
- `geosite:category-bank-ru`
- `geosite:category-gov-ru`
- `geosite:private`
- `geosite:category-ads-all`
```

- [ ] **Step 4: Verify download links match repository name**

Check the actual remote:

```bash
git remote -v
```

If the remote is `runetfreedom/research-v2ray-rules-dat-small`, replace download links with:

```markdown
- **geoip.dat**
    - [https://raw.githubusercontent.com/runetfreedom/research-v2ray-rules-dat-small/release/geoip.dat](https://raw.githubusercontent.com/runetfreedom/research-v2ray-rules-dat-small/release/geoip.dat)
- **geosite.dat**
    - [https://raw.githubusercontent.com/runetfreedom/research-v2ray-rules-dat-small/release/geosite.dat](https://raw.githubusercontent.com/runetfreedom/research-v2ray-rules-dat-small/release/geosite.dat)
```

If the remote is different, use the actual `owner/repo` from `git remote -v`.

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: document filtered geodata categories"
```

---

### Task 6: Final Verification

**Files:**
- No new files unless fixes are needed.

- [ ] **Step 1: Run full Python verification**

Run:

```bash
pytest -v
python3 -m py_compile tools/*.py
```

Expected: all tests PASS and compile exits 0.

- [ ] **Step 2: Run CLI tools on generated fixtures through pytest**

Run:

```bash
pytest tests/test_tools_cli.py -v
```

Expected: all CLI tests PASS.

- [ ] **Step 3: Review final diff**

Run:

```bash
git status --short
git diff --stat HEAD
git diff -- .github/workflows/build.yml tools README.md tests pytest.ini
```

Expected: changes are limited to the planned files.

- [ ] **Step 4: Commit remaining fixes if any**

If verification required additional edits:

```bash
git add .github/workflows/build.yml tools README.md tests pytest.ini
git commit -m "chore: finish geodata build hardening"
```

If there are no additional edits, skip this commit.

---

## Self-Review Notes

- Spec coverage: covers CI input validation, parser robustness, code duplication, README accuracy, and basic automated tests.
- Placeholder scan: no deferred implementation placeholders are required; each task includes concrete files, commands, and expected outcomes.
- Type consistency: shared parser API is `read_varint`, `encode_varint`, `encode_field_len`, `parse_entries`, `extract_categories`, `write_categories_file`, and `ProtoParseError`.
