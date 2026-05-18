# Independent Geodata Build Design

## Goal

Move this repository from filtering ready-made upstream `.dat` files to independently building geodata from primary text sources, then publishing three variants:

- `full`: complete locally built source dataset.
- `small`: reduced proxy/direct/block dataset.
- `internal`: Russian direct-only dataset for resources that should be routed through Russian/internal access.

The root files in the `release` branch are no longer the `small` variant. Root `geoip.dat` and `geosite.dat` are the `internal` variant.

## Current State

The current workflow downloads ready-made files from:

- `runetfreedom/russia-blocked-geoip/release/geoip.dat`
- `runetfreedom/russia-blocked-geosite/release/geosite.dat`

It then filters selected categories into root `publish/geoip.dat` and `publish/geosite.dat`.

This makes the repository dependent on upstream release artifacts. The new design removes that dependency.

## Build Inputs

The repository should download primary source lists directly. Initial source set:

- `antifilter.download` IP and domain lists.
- `community.antifilter.download` IP and domain lists.
- `re:filter` IP and domain lists.
- `v2fly/domain-list-community` for base geosite categories.
- Russian domain/category sources used for `category-ru`, `category-bank-ru`, `category-gov-ru`, and `ru-available-only-inside`.
- GeoIP/ASN sources needed for `ru`, `ru-whitelist`, `yandex`, `ddos-guard`, and service IP categories.
- Ad/block and Windows-related lists only if they remain required by `small` or `full`.

Exact source URLs should be represented in repository-owned config files, not hidden inside the workflow.

## Dataset Variants

### full

`full` is the locally built complete dataset. It contains source categories such as:

- blocked/proxy categories;
- Russian/direct categories;
- service categories;
- base geosite categories;
- generated GeoIP categories.

`full` exists primarily as the canonical local build artifact from which `small` and `internal` can be produced.

### small

`small` keeps the current reduced dataset semantics. It contains the selected proxy/direct/block categories currently published by this repository.

It is published only under:

```text
small/geoip.dat
small/geosite.dat
```

### internal

`internal` is a direct-only Russian/internal access dataset. It is not a mathematical inverse of `small`.

It must contain only resources that should be routed through Russian/internal access:

- Russian domains;
- Russian bank domains;
- Russian government domains;
- domains available only inside Russia;
- Russian IP ranges;
- selected Russian infrastructure categories;
- local/private entries if explicitly included.

Resources blocked in Russia must not be present in `internal`, even if they also appear in a Russian category.

## Internal Category Names

The first version uses explicit cleaned category names to avoid confusing them with raw `full` categories.

Geosite internal categories:

```text
internal-ru
internal-bank-ru
internal-gov-ru
internal-available-only-inside
internal-private
```

GeoIP internal categories:

```text
internal-ru
internal-ru-whitelist
internal-yandex
internal-ddos-guard
internal-private
```

## Internal Exclusion Rules

Internal categories must be physically cleaned before `.dat` generation. It is not enough to omit blocked categories from the output file.

For geosite:

```text
blocked_domain_set =
  ru-blocked
  + ru-blocked-all
  + antifilter-download
  + antifilter-download-community
  + refilter

internal-ru =
  category-ru - blocked_domain_set

internal-bank-ru =
  category-bank-ru - blocked_domain_set

internal-gov-ru =
  category-gov-ru - blocked_domain_set

internal-available-only-inside =
  ru-available-only-inside - blocked_domain_set
```

For geoip:

```text
blocked_ip_set =
  ru-blocked
  + ru-blocked-community
  + re-filter

internal-ru =
  ru - blocked_ip_set

internal-ru-whitelist =
  ru-whitelist - blocked_ip_set

internal-yandex =
  yandex - blocked_ip_set

internal-ddos-guard =
  ddos-guard - blocked_ip_set
```

If exact CIDR subtraction is needed, overlapping blocked CIDRs must be removed or split correctly rather than only dropping identical CIDR strings.

## Release Layout

The `release` branch should publish:

```text
geoip.dat
geosite.dat
geoip.dat.sha256sum
geosite.dat.sha256sum
geoip_categories.txt
geosite_categories.txt

internal/geoip.dat
internal/geosite.dat
internal/geoip.dat.sha256sum
internal/geosite.dat.sha256sum
internal/geoip_categories.txt
internal/geosite_categories.txt

small/geoip.dat
small/geosite.dat
small/geoip.dat.sha256sum
small/geosite.dat.sha256sum
small/geoip_categories.txt
small/geosite_categories.txt

full/geoip.dat
full/geosite.dat
full/geoip.dat.sha256sum
full/geosite.dat.sha256sum
full/geoip_categories.txt
full/geosite_categories.txt
```

Root files are duplicates of `internal`:

```text
geoip.dat = internal/geoip.dat
geosite.dat = internal/geosite.dat
```

The old root-file behavior is intentionally changed. Root URLs now return the internal dataset.

## Build Flow

1. Download primary source lists into a deterministic build cache.
2. Normalize source lists:
   - domains to canonical lowercase domain entries;
   - IPs to validated CIDR records;
   - remove comments, empty lines, and malformed entries.
3. Build source category sets.
4. Build blocked domain and blocked IP exclusion sets.
5. Build `full` `.dat` files.
6. Build `small` `.dat` files from configured categories.
7. Build cleaned `internal-*` categories by subtracting blocked sets.
8. Build `internal` `.dat` files.
9. Generate category lists and checksums for every variant.
10. Validate that required categories exist and that generated files are non-empty.
11. Publish all artifacts to a GitHub Release and force-push the `release` branch.

## Validation

The workflow must fail before publication if:

- any required source cannot be downloaded;
- a source file is empty;
- generated `.dat` files are empty;
- expected categories are missing;
- `internal` contains any category not prefixed with `internal-`;
- root `geoip.dat` or `geosite.dat` differs from the internal variant;
- category extraction from generated `.dat` fails.

Tests should cover:

- source normalization;
- domain set subtraction;
- CIDR overlap/subtraction behavior;
- `.dat` category generation;
- `small`, `full`, and `internal` release layout;
- root files matching internal files.

## Open Implementation Choice

The implementation can either vendor or call existing upstream build tools for final `.dat` encoding, but all source selection, internal category generation, and release layout must be owned by this repository.
