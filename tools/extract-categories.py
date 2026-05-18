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

from geodat_proto import extract_categories


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
