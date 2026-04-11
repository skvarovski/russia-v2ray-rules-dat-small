#!/usr/bin/env python3
"""
extract-categories.py — Extract category names from a filtered geosite.dat or geoip.dat.

Usage:
    python3 extract-categories.py geosite ./publish/geosite.dat ./publish/geosite_categories.txt
    python3 extract-categories.py geoip  ./publish/geoip.dat  ./publish/geoip_categories.txt

Reads the protobuf .dat file, extracts all country_code/category fields,
and writes them one per line to the output text file (sorted, uppercase).
"""

import sys
import os


def read_varint(data: bytes, pos: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while True:
        b = data[pos]; pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, pos
        shift += 7


def get_country_code(entry_data: bytes) -> str:
    pos = 0
    while pos < len(entry_data):
        tag_wire, pos = read_varint(entry_data, pos)
        field = tag_wire >> 3
        wire  = tag_wire & 7
        if wire == 0:
            _, pos = read_varint(entry_data, pos)
        elif wire == 2:
            length, pos = read_varint(entry_data, pos)
            payload = entry_data[pos:pos + length]
            pos += length
            if field == 1:
                return payload.decode('utf-8', errors='replace')
        elif wire == 1:
            pos += 8
        elif wire == 5:
            pos += 4
        else:
            break
    return ''


def extract_categories(data: bytes) -> list[str]:
    categories = []
    pos = 0
    while pos < len(data):
        tag_wire, pos = read_varint(data, pos)
        wire = tag_wire & 7
        if wire != 2:
            break
        length, pos = read_varint(data, pos)
        entry_data = data[pos:pos + length]
        pos += length
        code = get_country_code(entry_data)
        if code:
            categories.append(code.upper())
    return sorted(set(categories))


def main():
    if len(sys.argv) < 4:
        print(f'Usage: {sys.argv[0]} <geosite|geoip> <input.dat> <output.txt>', file=sys.stderr)
        sys.exit(1)

    dat_type = sys.argv[1]
    input_path = sys.argv[2]
    output_path = sys.argv[3]

    with open(input_path, 'rb') as f:
        data = f.read()

    categories = extract_categories(data)
    print(f'{dat_type}: {len(categories)} categories extracted from {input_path}')

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, 'w') as f:
        for cat in categories:
            f.write(cat + '\n')

    print(f'Written to {output_path}')


if __name__ == '__main__':
    main()
