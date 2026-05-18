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
