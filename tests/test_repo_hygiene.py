"""Guards for committed configuration files.

`.env.example` is tracked in a public repository, so it must stay a names-only template and
must list every environment variable the code reads. Failure messages print variable NAMES only,
never values.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SECRET_NAME = re.compile(r"(KEY|SECRET|TOKEN|PASSWORD|PASSWD|CREDENTIAL)", re.I)
# Variables the platform provides; they do not belong in the template.
PLATFORM_VARS = {"VERCEL_GIT_COMMIT_SHA"}


def _read_example() -> str:
    try:
        return (ROOT / ".env.example").read_text()
    except PermissionError:  # some sandboxes deny .env* reads; CI runs this for real
        pytest.skip("cannot read .env.example in this environment")


def _assignments(text: str):
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = re.sub(r"^export\s+", "", line)
        if "=" in line:
            name, _, value = line.partition("=")
            yield name.strip(), value.strip().strip("\"'")


def test_env_example_is_not_empty():
    assert len(list(_assignments(_read_example()))) >= 5


def test_env_example_contains_no_secret_values():
    leaked = [n for n, v in _assignments(_read_example()) if SECRET_NAME.search(n) and v]
    assert not leaked, (
        f"Real values for {leaked} must never be committed. Remove them, rotate the credential, "
        "and set it in the host's secret store instead."
    )


def test_env_example_lists_every_variable_the_code_reads():
    declared = {n for n, _ in _assignments(_read_example())}
    used = set()
    for path in [ROOT / "app.py", *(ROOT / "dealscope").glob("*.py")]:
        text = path.read_text()
        used |= set(re.findall(r'os\.environ\.get\(\s*"([A-Z0-9_]+)"', text))
        used |= set(re.findall(r'_float\(\s*"([A-Z0-9_]+)"', text))
    missing = sorted(used - declared - PLATFORM_VARS)
    assert not missing, f".env.example is missing: {missing}"


def test_gitignore_keeps_real_env_files_out_of_git():
    ignore = (ROOT / ".gitignore").read_text().splitlines()
    assert ".env" in ignore and ".env.*" in ignore and "!.env.example" in ignore
