#!/usr/bin/env python3
"""
filter-geosite.py — Extract specific categories from a geosite.dat file.

Usage:
    python3 filter-geosite.py [input.dat] [output.dat] [CATEGORY1 CATEGORY2 ...]

Defaults:
    input  = ../geodata/geosite.dat  (relative to this script)
    output = ./geosite-filtered.dat
    categories = the 24 standard podkop-xray categories

Protobuf schema (no library needed — pure Python struct parsing):
    GeoSiteList  { repeated GeoSite entry = 1; }
    GeoSite      { string country_code = 1; repeated Domain domain = 2; }
    Domain       { Type type=1; string value=2; repeated Attribute attribute=3; }

The script reads the binary protobuf, locates entries whose country_code matches
one of the requested categories (case-insensitive), and writes a new GeoSiteList
containing only those entries — preserving all domain records byte-for-byte.
"""

import sys
import os

# ---------------------------------------------------------------------------
# Default configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_INPUT  = os.path.join(SCRIPT_DIR, '..', '..', 'geodata', 'geosite.dat')
DEFAULT_OUTPUT = os.path.join(SCRIPT_DIR, 'geosite-filtered.dat')

DEFAULT_CATEGORIES = [
    # Proxy (18 categories)
    'RU-BLOCKED',
    'ANTIFILTER-DOWNLOAD-COMMUNITY',
    'CATEGORY-MEDIA',
    'CATEGORY-COMMUNICATION',
    'CATEGORY-SOCIAL-MEDIA-!CN',
    'CATEGORY-ENTERTAINMENT',
    'CATEGORY-GAMES',
    'CATEGORY-DEV',
    'CATEGORY-FORUMS',
    'CATEGORY-AI-!CN',
    'CATEGORY-ANTICENSORSHIP',
    'CATEGORY-VPNSERVICES',
    'CATEGORY-CRYPTOCURRENCY',
    'CATEGORY-SCHOLAR-!CN',
    'CATEGORY-CDN-!CN',
    'GOOGLE',
    'CLOUDFLARE',
    'AMAZON',
    # Direct (5 categories, 4 default + PRIVATE available)
    'CATEGORY-RU',
    'RU-AVAILABLE-ONLY-INSIDE',
    'CATEGORY-BANK-RU',
    'CATEGORY-GOV-RU',
    'PRIVATE',
    # Block (1 category)
    'CATEGORY-ADS-ALL',
]

# ---------------------------------------------------------------------------
# Protobuf primitive helpers (no external library)
# ---------------------------------------------------------------------------

def read_varint(data: bytes, pos: int) -> tuple[int, int]:
    """Decode a base-128 varint starting at pos; return (value, new_pos)."""
    result = 0
    shift = 0
    while True:
        b = data[pos]; pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, pos
        shift += 7


def encode_varint(value: int) -> bytes:
    """Encode an integer as a base-128 varint."""
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
    """Encode a length-delimited protobuf field (wire type 2)."""
    tag = (field_number << 3) | 2
    return encode_varint(tag) + encode_varint(len(payload)) + payload


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def get_country_code(entry_data: bytes) -> str:
    """
    Extract the country_code (field 1, wire type 2) from a raw GeoSite blob.
    Returns the code string, or '' if not found.
    """
    pos = 0
    while pos < len(entry_data):
        tag_wire, pos = read_varint(entry_data, pos)
        field = tag_wire >> 3
        wire  = tag_wire & 7
        if wire == 0:          # varint — skip
            _, pos = read_varint(entry_data, pos)
        elif wire == 2:        # length-delimited
            length, pos = read_varint(entry_data, pos)
            payload = entry_data[pos:pos + length]
            pos += length
            if field == 1:     # country_code
                return payload.decode('utf-8', errors='replace')
        elif wire == 1:        # 64-bit — skip
            pos += 8
        elif wire == 5:        # 32-bit — skip
            pos += 4
        else:
            break              # unknown wire type — stop
    return ''


def parse_entries(data: bytes) -> list[tuple[str, bytes]]:
    """
    Parse the top-level GeoSiteList message.
    Returns a list of (country_code, raw_entry_bytes) pairs — one per GeoSite.
    raw_entry_bytes is the *inner* payload (GeoSite message, without its outer tag/length).
    """
    entries = []
    pos = 0
    while pos < len(data):
        tag_wire, pos = read_varint(data, pos)
        field = tag_wire >> 3
        wire  = tag_wire & 7
        if wire != 2:
            # Unexpected — stop parsing
            print(f'  [warn] unexpected wire type {wire} (field {field}) at offset {pos-1}', file=sys.stderr)
            break
        length, pos = read_varint(data, pos)
        entry_data = data[pos:pos + length]
        pos += length
        if field == 1:         # GeoSiteList.entry
            code = get_country_code(entry_data)
            entries.append((code, entry_data))
    return entries


# ---------------------------------------------------------------------------
# Category list output
# ---------------------------------------------------------------------------

def write_categories_file(entries: list[tuple[str, bytes]], output_path: str):
    """Write a sorted list of category names (one per line) to a text file."""
    codes = sorted({code.upper() for code, _ in entries if code})
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, 'w') as f:
        f.write('\n'.join(codes) + '\n')
    print(f'Categories file: {output_path} ({len(codes)} entries)')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]
    input_path  = args[0] if len(args) > 0 else DEFAULT_INPUT
    output_path = args[1] if len(args) > 1 else DEFAULT_OUTPUT
    categories  = [c.upper() for c in args[2:]] if len(args) > 2 else DEFAULT_CATEGORIES

    wanted = set(c.upper() for c in categories)

    print(f'Input : {input_path}')
    print(f'Output: {output_path}')
    print(f'Want  : {sorted(wanted)}')

    with open(input_path, 'rb') as f:
        data = f.read()
    print(f'Read {len(data):,} bytes ({len(data)//1024//1024} MB)')

    entries = parse_entries(data)
    print(f'Total categories in file: {len(entries)}')

    selected = [(code, blob) for code, blob in entries if code.upper() in wanted]
    found_codes = {code.upper() for code, _ in selected}
    missing = wanted - found_codes
    if missing:
        print(f'[WARN] Not found in file: {sorted(missing)}')

    print(f'Selected: {len(selected)} categories — {sorted(found_codes)}')

    # Write category list files (derived from output_path: .dat -> .txt / _full.txt)
    base = output_path.rsplit('.', 1)[0] if '.' in output_path else output_path
    write_categories_file(entries, base + '_full.txt')
    write_categories_file(selected, base + '.txt')

    # Rebuild GeoSiteList: each entry encoded as field 1, wire type 2
    out_parts = [encode_field_len(1, blob) for _, blob in selected]
    out_data = b''.join(out_parts)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(out_data)

    in_mb  = len(data) / 1024 / 1024
    out_mb = len(out_data) / 1024 / 1024
    print(f'Written {len(out_data):,} bytes ({out_mb:.2f} MB)  —  {out_mb/in_mb*100:.1f}% of original')
    print('Done.')


if __name__ == '__main__':
    main()
