#!/usr/bin/env python3
"""Fail if tracked or staged files contain what looks like a real secret.

Usage:
  scripts/scan_secrets.py --staged      # files staged for commit (pre-commit hook)
  scripts/scan_secrets.py --all         # every tracked file (CI)
  scripts/scan_secrets.py PATH [...]    # explicit files

Findings print FILE:LINE and the rule name only. The matched text is never printed, so the
scanner itself cannot leak what it finds. Add `secret-scan: allow` on a line to exempt it.

Rules
  assign  KEY/SECRET/TOKEN/PASSWORD-style variable given a non-placeholder value, in env-like
          and config files (.env*, yaml, shell, toml, ini, Dockerfile, Makefile)
  token   well-known credential shapes anywhere (cloud keys, GitHub/Anthropic/OpenAI/Slack
          tokens, private key blocks, hex API keys next to an api-key label)
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

ASSIGN_FILES = re.compile(
    r"(^|/)(\.env[^/]*|[^/]+\.(ya?ml|sh|toml|ini|cfg|conf)|Dockerfile|Makefile)$", re.I
)
ASSIGN = re.compile(
    r"^\s*(?:export\s+)?(?P<name>[A-Za-z0-9_.-]*(?:KEY|SECRET|TOKEN|PASSWORD|PASSWD|CREDENTIAL)"
    r"[A-Za-z0-9_.-]*)\s*[:=]\s*(?P<value>.*)$",
    re.I,
)
PLACEHOLDER = re.compile(
    r"^(\$|<|\{\{|\*+$|\.\.\.|x{3,}|your[-_ ]|example|changeme|redacted|none$|null$|false$|true$)",
    re.I,
)
TOKEN_RULES: List[Tuple[str, "re.Pattern[str]"]] = [
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b")),
    ("github-pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b")),
    ("anthropic-key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("openai-style-key", re.compile(r"\bsk-[A-Za-z0-9]{32,}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("private-key-block", re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")),
    (
        "hex-api-key",
        re.compile(r"(?i)(?:api[_-]?key|x-api-key)[\"'\s:=]{1,6}[0-9a-f]{32}\b"),
    ),
]
ALLOW_MARK = "secret-scan: allow"
SKIP_DIRS = ("data/", ".git/", "node_modules/", ".venv/", "venv/")
MAX_BYTES = 1_000_000


def _git(*args: str) -> List[str]:
    out = subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout
    return [line for line in out.splitlines() if line]


def _clean_value(raw: str) -> str:
    value = raw.strip()
    if value.startswith("#"):  # an inline comment, not a value
        return ""
    if value and value[0] in "\"'":
        quote = value[0]
        end = value.find(quote, 1)
        value = value[1:end] if end > 0 else value[1:]
    else:
        value = re.split(r"\s+#", value, maxsplit=1)[0].strip()
    return value


def scan_text(path: str, text: str) -> List[Tuple[str, int, str]]:
    findings: List[Tuple[str, int, str]] = []
    check_assign = bool(ASSIGN_FILES.search(path))
    for number, line in enumerate(text.splitlines(), start=1):
        if ALLOW_MARK in line:
            continue
        for rule, pattern in TOKEN_RULES:
            if pattern.search(line):
                findings.append((path, number, rule))
        if check_assign:
            match = ASSIGN.match(line)
            if match:
                value = _clean_value(match.group("value"))
                if len(value) >= 8 and not PLACEHOLDER.match(value):
                    findings.append((path, number, "assign"))
    return findings


def _read(path: str, staged: bool) -> Optional[str]:
    try:
        if staged:
            data = subprocess.run(
                ["git", "show", f":{path}"], capture_output=True, check=True
            ).stdout
        else:
            data = Path(path).read_bytes()
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"skipped (unreadable): {path} [{type(exc).__name__}]", file=sys.stderr)
        return None
    if len(data) > MAX_BYTES or b"\0" in data[:2048]:
        return None
    return data.decode("utf-8", errors="replace")


def scan_paths(paths: Iterable[str], staged: bool = False) -> List[Tuple[str, int, str]]:
    findings: List[Tuple[str, int, str]] = []
    for path in paths:
        if path.startswith(SKIP_DIRS) or path == "scripts/scan_secrets.py":
            continue
        text = _read(path, staged)
        if text is not None:
            findings.extend(scan_text(path, text))
    return findings


def main(argv: List[str]) -> int:
    if argv == ["--staged"]:
        paths = _git("diff", "--cached", "--name-only", "--diff-filter=ACM")
        staged = True
    elif argv == ["--all"]:
        paths, staged = _git("ls-files"), False
    elif argv and not argv[0].startswith("--"):
        paths, staged = argv, False
    else:
        print(__doc__)
        return 2
    findings = scan_paths(paths, staged)
    for path, number, rule in findings:
        print(f"SECRET? {path}:{number} [{rule}]")
    if findings:
        print(
            "\nPossible secret(s) found (values not shown). Remove them, rotate the credential if "
            "it was ever pushed, and use the host's secret store. Intentional false positive? "
            f"Add '{ALLOW_MARK}' to that line.",
            file=sys.stderr,
        )
        return 1
    print(f"secret scan: ok ({len(paths)} file(s) checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
