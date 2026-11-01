from pathlib import Path

from fastkwan.config import Settings

EXAMPLE = Path(__file__).resolve().parent.parent / ".env.example"


def names_in_example():
    names = set()
    for line in EXAMPLE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            names.add(line.split("=", 1)[0].strip())
    return names


def test_every_setting_is_documented_in_the_example_file():
    documented = names_in_example()
    missing = {name.upper() for name in Settings.model_fields} - documented
    assert missing == set(), f"add these to .env.example: {sorted(missing)}"


def test_the_example_file_names_no_unknown_setting():
    unknown = names_in_example() - {name.upper() for name in Settings.model_fields}
    assert unknown == set(), f"not settings (typo or removed?): {sorted(unknown)}"
