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
