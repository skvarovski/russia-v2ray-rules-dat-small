from pathlib import Path

from tools.build_dat import (
    build_internal_geoip,
    build_internal_geosite,
    normalize_cidr_token,
    normalize_domain_token,
    parse_cidr_list,
    parse_asn_csv,
    parse_domain_list,
    parse_domain_list_with_includes,
    validate_output,
    write_variant,
    copy_internal_to_root,
)


def test_parse_domain_list_normalizes_supported_domain_list_lines():
    text = """
    # comment
    domain:Example.RU @ru
    full:Sub.Example.RU
    include:google
    regexp:^bad$
    """

    assert parse_domain_list(text) == {"example.ru", "sub.example.ru"}


def test_parse_domain_list_with_includes_loads_referenced_categories():
    text = """
    include:messenger
    domain:chat.example
    """

    def load_include(name):
        assert name == "messenger"
        return {"messenger.example"}

    assert parse_domain_list_with_includes(text, load_include) == {"chat.example", "messenger.example"}


def test_parse_cidr_list_normalizes_networks_and_ignores_bad_lines():
    text = """
    192.0.2.1
    10.0.0.0/8
    not-a-network
    """

    assert parse_cidr_list(text) == {"192.0.2.1/32", "10.0.0.0/8"}
    assert normalize_cidr_token("geoip:private") is None


def test_parse_asn_csv_selects_wanted_networks():
    text = """network,autonomous_system_number,autonomous_system_organization
192.0.2.0/24,13238,YANDEX LLC
198.51.100.0/24,64500,Other
"""

    assert parse_asn_csv(text, {13238}) == {"192.0.2.0/24"}


def test_normalize_domain_token_rejects_non_domain_rules():
    assert normalize_domain_token("include:category-ru") is None
    assert normalize_domain_token("regexp:^example") is None
    assert normalize_domain_token("https://example.ru") is None


def test_build_internal_geosite_subtracts_blocked_domains():
    categories = {
        "category-ru": {"ok.ru", "blocked.ru"},
        "ru-blocked": {"blocked.ru"},
        "refilter": {"other.ru"},
    }

    result = build_internal_geosite(categories, {"internal-ru": "category-ru"}, ["ru-blocked", "refilter"])

    assert result == {"internal-ru": {"ok.ru"}}


def test_build_internal_geoip_drops_overlapping_blocked_networks():
    categories = {
        "ru": {"192.0.2.0/24", "198.51.100.0/24", "2001:db8::/32"},
        "ru-blocked": {"192.0.2.0/25"},
    }

    result = build_internal_geoip(categories, {"internal-ru": "ru"}, ["ru-blocked"])

    assert result == {"internal-ru": {"192.0.2.128/25", "198.51.100.0/24", "2001:db8::/32"}}


def test_write_variant_and_root_internal_layout(tmp_path: Path):
    write_variant(tmp_path, "internal", {"internal-ru": {"example.ru"}}, {"internal-ru": {"192.0.2.0/24"}})
    write_variant(tmp_path, "small", {"ru-blocked": {"blocked.ru"}}, {"ru-blocked": {"198.51.100.0/24"}})
    write_variant(tmp_path, "full", {"category-ru": {"example.ru"}}, {"ru": {"192.0.2.0/24"}})
    copy_internal_to_root(tmp_path)

    validate_output(tmp_path)
    assert (tmp_path / "geosite.dat").read_bytes() == (tmp_path / "internal" / "geosite.dat").read_bytes()
    assert (tmp_path / "geoip.dat").read_bytes() == (tmp_path / "internal" / "geoip.dat").read_bytes()
