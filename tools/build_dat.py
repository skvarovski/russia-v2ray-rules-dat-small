#!/usr/bin/env python3
import argparse
import csv
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tarfile
from bisect import bisect_right
from ipaddress import ip_address, ip_network, summarize_address_range
from pathlib import Path
from urllib.request import Request, urlopen

try:
    from geodat_proto import encode_geoip_list, encode_geosite_list, extract_categories
except ModuleNotFoundError:
    from tools.geodat_proto import encode_geoip_list, encode_geosite_list, extract_categories

PRIVATE_DOMAINS = {"localhost", "local"}
PRIVATE_CIDRS = [
    "0.0.0.0/8",
    "10.0.0.0/8",
    "100.64.0.0/10",
    "127.0.0.0/8",
    "169.254.0.0/16",
    "172.16.0.0/12",
    "192.0.0.0/24",
    "192.0.2.0/24",
    "192.168.0.0/16",
    "198.18.0.0/15",
    "198.51.100.0/24",
    "203.0.113.0/24",
    "::1/128",
    "fc00::/7",
    "fe80::/10",
]

DOMAIN_PREFIXES = ("domain:", "full:", "regexp:", "keyword:")
DLC_ARCHIVE_URL = "https://github.com/v2fly/domain-list-community/archive/refs/heads/master.tar.gz"


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def fetch_text(url: str, timeout: int = 60) -> str:
    print(f"Fetch: {url}", file=sys.stderr)
    request = Request(url, headers={"User-Agent": "russia-v2ray-rules-dat-small-builder/1.0"})
    with urlopen(request, timeout=timeout) as response:
        data = response.read()
    if not data:
        raise ValueError(f"empty source: {url}")
    return data.decode("utf-8", errors="replace")


def fetch_bytes(url: str, timeout: int = 120) -> bytes:
    print(f"Fetch: {url}", file=sys.stderr)
    request = Request(url, headers={"User-Agent": "russia-v2ray-rules-dat-small-builder/1.0"})
    with urlopen(request, timeout=timeout) as response:
        data = response.read()
    if not data:
        raise ValueError(f"empty source: {url}")
    return data


def load_dlc_data() -> dict[str, str]:
    archive = fetch_bytes(DLC_ARCHIVE_URL)
    data = {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        for member in tar.getmembers():
            marker = "/data/"
            if marker not in member.name or not member.isfile():
                continue
            name = member.name.split(marker, 1)[1]
            extracted = tar.extractfile(member)
            if extracted is None:
                continue
            data[name] = extracted.read().decode("utf-8", errors="replace")
    if not data:
        raise ValueError("domain-list-community archive has no data files")
    return data


def strip_comment(line: str) -> str:
    line = line.strip()
    for marker in ("#", "//"):
        if marker in line:
            line = line.split(marker, 1)[0].strip()
    return line


def normalize_domain_token(token: str) -> str | None:
    token = strip_comment(token).lower()
    if not token or token.startswith(("include:", "ext:", "regexp:", "keyword:")):
        return None
    for prefix in DOMAIN_PREFIXES:
        if token.startswith(prefix):
            token = token.split(":", 1)[1]
            break
    token = token.lstrip(".")
    token = token.rstrip(".")
    if token.startswith("@"):
        return None
    if ":" in token or "/" in token:
        return None
    if not re.fullmatch(r"[a-z0-9*_-]+(\.[a-z0-9*_-]+)+|localhost|local", token):
        return None
    return token


def parse_domain_list(text: str) -> set[str]:
    domains = set()
    for line in text.splitlines():
        token = strip_comment(line)
        if not token:
            continue
        domain = normalize_domain_token(token.split()[0])
        if domain:
            domains.add(domain)
    return domains


def parse_domain_list_with_includes(text: str, include_loader) -> set[str]:
    domains = parse_domain_list(text)
    for line in text.splitlines():
        token = strip_comment(line).lower()
        if not token.startswith("include:"):
            continue
        include_name = token.split(":", 1)[1].split("@", 1)[0].strip()
        if include_name:
            domains.update(include_loader(include_name))
    return domains


def normalize_cidr_token(token: str) -> str | None:
    token = strip_comment(token)
    if not token:
        return None
    token = token.split()[0]
    if token.startswith(("geoip:", "include:", "ext:")):
        return None
    try:
        return str(ip_network(token, strict=False))
    except ValueError:
        return None


def parse_cidr_list(text: str) -> set[str]:
    cidrs = set()
    for line in text.splitlines():
        cidr = normalize_cidr_token(line)
        if cidr:
            cidrs.add(cidr)
    return cidrs


def parse_asn_csv(text: str, wanted_asns: set[int]) -> set[str]:
    cidrs = set()
    for row in csv.DictReader(text.splitlines()):
        try:
            asn = int(row["autonomous_system_number"])
        except (KeyError, TypeError, ValueError):
            continue
        if asn not in wanted_asns:
            continue
        cidr = normalize_cidr_token(row.get("network", ""))
        if cidr:
            cidrs.add(cidr)
    return cidrs


def subtract_cidrs(values: set[str], blocked: set[str]) -> set[str]:
    blocked_by_version = {4: [], 6: []}
    for cidr in blocked:
        network = ip_network(cidr, strict=False)
        blocked_by_version[network.version].append((int(network.network_address), int(network.broadcast_address)))
    for version in blocked_by_version:
        blocked_by_version[version] = merge_intervals(blocked_by_version[version])
    starts_by_version = {
        version: [item[0] for item in intervals]
        for version, intervals in blocked_by_version.items()
    }

    result = set()
    for cidr in values:
        network = ip_network(cidr, strict=False)
        start = int(network.network_address)
        end = int(network.broadcast_address)
        for remaining_start, remaining_end in subtract_intervals(
            start,
            end,
            blocked_by_version[network.version],
            starts_by_version[network.version],
        ):
            start_address = ip_address(remaining_start)
            end_address = ip_address(remaining_end)
            result.update(str(part) for part in summarize_address_range(start_address, end_address))
    return result


def merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1] + 1:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return merged


def subtract_intervals(
    start: int,
    end: int,
    blocked: list[tuple[int, int]],
    blocked_starts: list[int],
) -> list[tuple[int, int]]:
    if not blocked:
        return [(start, end)]
    index = max(0, bisect_right(blocked_starts, start) - 1)
    cursor = start
    result = []
    while index < len(blocked):
        blocked_start, blocked_end = blocked[index]
        if blocked_start > end:
            break
        if blocked_end < cursor:
            index += 1
            continue
        if blocked_start > cursor:
            result.append((cursor, min(blocked_start - 1, end)))
        cursor = max(cursor, blocked_end + 1)
        if cursor > end:
            break
        index += 1
    if cursor <= end:
        result.append((cursor, end))
    return result


def load_source_categories(source_config: dict[str, list[str]], parser) -> dict[str, set[str]]:
    categories = {}
    for category, urls in source_config.items():
        values = set()
        for url in urls:
            values.update(parser(fetch_text(url)))
        categories[category] = values
        print(f"Loaded {category}: {len(values)} entries", file=sys.stderr)
    return categories


def load_geosite_categories(source_config: dict[str, list[str]]) -> dict[str, set[str]]:
    include_cache = {}
    dlc_data = None

    def load_dlc_include(name: str) -> set[str]:
        nonlocal dlc_data
        if dlc_data is None:
            dlc_data = load_dlc_data()
        if name in include_cache:
            return include_cache[name]
        if name not in dlc_data:
            raise ValueError(f"missing domain-list-community include: {name}")
        text = dlc_data[name]
        include_cache[name] = set()
        include_cache[name] = parse_domain_list_with_includes(text, load_dlc_include)
        return include_cache[name]

    categories = {}
    for category, urls in source_config.items():
        values = set()
        for url in urls:
            if "v2fly/domain-list-community" in url:
                name = url.rstrip("/").rsplit("/", 1)[1]
                values.update(load_dlc_include(name))
            else:
                text = fetch_text(url)
                values.update(parse_domain_list(text))
        categories[category] = values
        print(f"Loaded {category}: {len(values)} entries", file=sys.stderr)
    return categories


def load_asn_categories(asn_config: dict) -> dict[str, set[str]]:
    if not asn_config:
        return {}
    csv_texts = [fetch_text(asn_config["ipv4"]), fetch_text(asn_config["ipv6"])]
    categories = {}
    for category, asns in asn_config["wanted"].items():
        wanted = {int(asn) for asn in asns}
        values = set()
        for text in csv_texts:
            values.update(parse_asn_csv(text, wanted))
        categories[category] = values
        print(f"Loaded ASN {category}: {len(values)} entries", file=sys.stderr)
    return categories


def add_builtin_categories(geosite: dict[str, set[str]], geoip: dict[str, set[str]]) -> None:
    geosite.setdefault("private", set()).update(PRIVATE_DOMAINS)
    geoip.setdefault("private", set()).update(PRIVATE_CIDRS)


def select_categories(categories: dict[str, set[str]], names: list[str]) -> dict[str, set[str]]:
    selected = {}
    missing = []
    for name in names:
        values = categories.get(name)
        if values is None:
            missing.append(name)
            continue
        selected[name] = set(values)
    if missing:
        raise ValueError(f"missing categories: {', '.join(sorted(missing))}")
    return selected


def build_internal_geosite(categories: dict[str, set[str]], mapping: dict[str, str], blocked_names: list[str]) -> dict[str, set[str]]:
    blocked = set()
    for name in blocked_names:
        blocked.update(categories.get(name, set()))
    return {
        internal_name: set(categories.get(source_name, set())) - blocked
        for internal_name, source_name in mapping.items()
    }


def build_internal_geoip(categories: dict[str, set[str]], mapping: dict[str, str], blocked_names: list[str]) -> dict[str, set[str]]:
    blocked = set()
    for name in blocked_names:
        blocked.update(categories.get(name, set()))
    return {
        internal_name: subtract_cidrs(set(categories.get(source_name, set())), blocked)
        for internal_name, source_name in mapping.items()
    }


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_sha256(path: Path) -> None:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    write_text(path.with_name(path.name + ".sha256sum"), f"{digest}  {path.name}\n")


def write_variant(output_dir: Path, variant: str, geosite: dict[str, set[str]], geoip: dict[str, set[str]]) -> None:
    print(f"Write variant: {variant}", file=sys.stderr)
    variant_dir = output_dir / variant
    variant_dir.mkdir(parents=True, exist_ok=True)
    geosite_path = variant_dir / "geosite.dat"
    geoip_path = variant_dir / "geoip.dat"
    geosite_path.write_bytes(encode_geosite_list({k: sorted(v) for k, v in geosite.items()}))
    geoip_path.write_bytes(encode_geoip_list({k: sorted(v) for k, v in geoip.items()}))
    write_sha256(geosite_path)
    write_sha256(geoip_path)
    write_text(variant_dir / "geosite_categories.txt", "\n".join(extract_categories(geosite_path.read_bytes())) + "\n")
    write_text(variant_dir / "geoip_categories.txt", "\n".join(extract_categories(geoip_path.read_bytes())) + "\n")


def copy_internal_to_root(output_dir: Path) -> None:
    for name in (
        "geoip.dat",
        "geosite.dat",
        "geoip.dat.sha256sum",
        "geosite.dat.sha256sum",
        "geoip_categories.txt",
        "geosite_categories.txt",
    ):
        shutil.copyfile(output_dir / "internal" / name, output_dir / name)


def validate_output(output_dir: Path) -> None:
    for variant in ("full", "small", "internal"):
        for name in ("geoip.dat", "geosite.dat", "geoip_categories.txt", "geosite_categories.txt"):
            path = output_dir / variant / name
            if not path.exists() or path.stat().st_size == 0:
                raise ValueError(f"missing or empty artifact: {path}")
    for name in ("geoip.dat", "geosite.dat"):
        if (output_dir / name).read_bytes() != (output_dir / "internal" / name).read_bytes():
            raise ValueError(f"root {name} does not match internal/{name}")
    for category_file in ("geoip_categories.txt", "geosite_categories.txt"):
        categories = (output_dir / "internal" / category_file).read_text(encoding="utf-8").splitlines()
        bad = [category for category in categories if not category.startswith("INTERNAL-")]
        if bad:
            raise ValueError(f"internal contains non-internal categories: {bad}")


def build(config: dict, output_dir: Path) -> None:
    source_config = config["sources"]
    geosite_full = load_geosite_categories(source_config["geosite"])
    geoip_full = load_source_categories(source_config["geoip"], parse_cidr_list)
    geoip_full.update(load_asn_categories(source_config.get("geoip_asn", {})))
    add_builtin_categories(geosite_full, geoip_full)

    small_geosite = select_categories(geosite_full, config["small"]["geosite"])
    small_geoip = select_categories(geoip_full, config["small"]["geoip"])
    internal_geosite = build_internal_geosite(geosite_full, config["internal"]["geosite"], config["blocked"]["geosite"])
    internal_geoip = build_internal_geoip(geoip_full, config["internal"]["geoip"], config["blocked"]["geoip"])

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    write_variant(output_dir, "full", geosite_full, geoip_full)
    write_variant(output_dir, "small", small_geosite, small_geoip)
    write_variant(output_dir, "internal", internal_geosite, internal_geoip)
    copy_internal_to_root(output_dir)
    validate_output(output_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build full, small, and internal geodata variants from source lists.")
    parser.add_argument("--config", default="config/sources.json")
    parser.add_argument("--output", default="publish")
    args = parser.parse_args()

    config = load_config(Path(args.config))
    build(config, Path(args.output))
    print(f"Written geodata variants to {args.output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
