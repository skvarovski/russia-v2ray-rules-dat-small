import pytest

from tools.geodat_proto import (
    ProtoParseError,
    encode_field_len,
    encode_geoip_list,
    encode_geosite_list,
    encode_varint,
    extract_categories,
    parse_entries,
)


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


def test_filter_round_trip_can_rebuild_selected_entries():
    entries = parse_entries(make_dat("GOOGLE", "RU", "PRIVATE"))
    selected = [(code, blob) for code, blob in entries if code.upper() in {"GOOGLE", "PRIVATE"}]
    output = b"".join(encode_field_len(1, blob) for _, blob in selected)

    assert extract_categories(output) == ["GOOGLE", "PRIVATE"]


def test_encode_geosite_list_writes_category_entries():
    data = encode_geosite_list({"internal-ru": ["example.ru"], "internal-bank-ru": ["bank.ru"]})

    assert extract_categories(data) == ["INTERNAL-BANK-RU", "INTERNAL-RU"]


def test_encode_geoip_list_writes_category_entries():
    data = encode_geoip_list({"internal-ru": ["192.0.2.0/24"], "internal-private": ["10.0.0.0/8"]})

    assert extract_categories(data) == ["INTERNAL-PRIVATE", "INTERNAL-RU"]
