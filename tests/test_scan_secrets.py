"""The secret scanner must catch real-looking credentials and never print their values.

Dummy credentials are assembled at runtime so this file itself stays clean under the scan.
"""

import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("scan_secrets", ROOT / "scripts" / "scan_secrets.py")
scan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scan)

HEX32 = "0123456789abcdef" * 2


def rules(path, text):
    return [(n, r) for _, n, r in scan.scan_text(path, text)]


def test_filled_secret_variable_in_an_env_file_is_flagged():
    found = {r for _, r in rules(".env.example", f"RENTCAST_API_KEY={HEX32}\n")}
    assert "assign" in found  # the hex shape may also trip the token rule; either way it fails
    assert rules("deploy/.env.prod", "export DB_PASSWORD='hunter2hunter2'\n") == [(1, "assign")]
    assert rules("ci.yml", "  API_TOKEN: abcdefgh12345678\n") == [(1, "assign")]


@pytest.mark.parametrize(
    "line",
    [
        "RENTCAST_API_KEY=",
        "RENTCAST_API_KEY=   # leave empty",
        "API_TOKEN=${{ secrets.API_TOKEN }}",
        "SECRET_KEY=$SECRET_KEY",
        "API_KEY=<paste-key-here>",
        "PASSWORD=changeme-please",
        "TOKEN=your-token-here",
        "API_KEY=xxxxxxxxxxxx",
        "API_KEY=short",
        "# API_KEY=0123456789abcdef0123456789abcdef  secret-scan: allow",
    ],
)
def test_empty_placeholder_and_allowed_lines_are_not_flagged(line):
    assert rules(".env.example", line + "\n") == []


def test_assignment_rule_only_applies_to_config_files_not_source_or_tests():
    assert rules("tests/test_x.py", 'api_key = "test-key-value-123"\n') == []
    assert rules("README.md", "API_KEY=abcdefgh12345678\n") == []


@pytest.mark.parametrize(
    "rule,text",
    [
        ("aws-access-key", "id = " + "AKIA" + "ABCDEFGHIJKLMNOP"),
        ("github-token", "t = " + "ghp_" + "a1" * 20),
        ("anthropic-key", "k = " + "sk-ant-" + "api03-abcdefghijklmnopqrstuvwxyz"),
        ("slack-token", "s = " + "xox" + "b-1234567890-abcdefghij"),
        ("private-key-block", "-----BEGIN " + "RSA PRIVATE KEY-----"),
        ("hex-api-key", 'headers = {"X-Api-Key": "' + HEX32 + '"}'),
    ],
)
def test_well_known_credential_shapes_are_flagged_in_any_file(rule, text):
    assert [r for _, r in rules("app/anything.py", text + "\n")] == [rule]


def test_scanner_output_never_contains_the_secret_value(tmp_path, capsys):
    secret = HEX32
    f = tmp_path / ".env.local"
    f.write_text(f"RENTCAST_API_KEY={secret}\n")
    code = scan.main([str(f)])
    out = capsys.readouterr()
    assert code == 1
    assert secret not in out.out and secret not in out.err
    assert "[assign]" in out.out


def test_clean_file_passes_and_exit_codes(tmp_path, capsys):
    f = tmp_path / ".env.example"
    f.write_text("PORT=5000\nRENTCAST_API_KEY=\n")
    assert scan.main([str(f)]) == 0
    assert scan.main([]) == 2


def test_data_directory_and_the_scanner_itself_are_skipped():
    assert scan.scan_paths(["data/zip_market.json", "scripts/scan_secrets.py"]) == []


def test_repository_is_clean_under_the_scanner():
    try:
        tracked = subprocess.run(
            ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("not a git checkout")
    findings = scan.scan_paths([str(ROOT / p) for p in tracked])
    assert findings == [], f"possible secrets at {[(Path(p).name, n, r) for p, n, r in findings]}"
