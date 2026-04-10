#!/usr/bin/env python3
"""
filter-geoip.py — Extract specific categories from a geoip.dat file.

Usage:
    python3 filter-geoip.py [input.dat] [output.dat] [CATEGORY1 CATEGORY2 ...]

Defaults:
    input  = ../geodata/geoip.dat  (relative to this script)
    output = ./geoip-filtered.dat
    categories = the 11 standard podkop-xray categories

Protobuf schema (no library needed — pure Python struct parsing):
    GeoIPList  { repeated GeoIP entry = 1; }
    GeoIP      { string country_code = 1; repeated CIDR cidr = 2; }
    CIDR       { bytes ip = 1; int32 prefix = 2; }

The script reads the binary protobuf, locates entries whose country_code matches
one of the requested categories (case-insensitive), and writes a new GeoIPList
containing only those entries — preserving all CIDR records byte-for-byte.
"""

import sys
import os

# ---------------------------------------------------------------------------
# Default configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_INPUT  = os.path.join(SCRIPT_DIR, '..', '..', 'geodata', 'geoip.dat')
DEFAULT_OUTPUT = os.path.join(SCRIPT_DIR, 'geoip-filtered.dat')

DEFAULT_CATEGORIES = [
    # Proxy/Block — block lists by IP (4)
    'RU-BLOCKED',
    'RE-FILTER',
    'RU-BLOCKED-COMMUNITY',
    # Proxy — individual services by IP (3)
    'TELEGRAM',
    'GOOGLE',
    'CLOUDFLARE',
    # Direct — Russian IP ranges (4)
    'RU',
    'RU-WHITELIST',
    'YANDEX',
    'DDOS-GUARD',
    # Always (1)
    'PRIVATE',
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
    Extract the country_code (field 1, wire type 2) from a raw GeoIP blob.
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
    Parse the top-level GeoIPList message.
    Returns a list of (country_code, raw_entry_bytes) pairs — one per GeoIP.
    raw_entry_bytes is the *inner* payload (GeoIP message, without its outer tag/length).
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
        if field == 1:         # GeoIPList.entry
            code = get_country_code(entry_data)
            entries.append((code, entry_data))
    return entries


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

    # Rebuild GeoIPList: each entry encoded as field 1, wire type 2
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
