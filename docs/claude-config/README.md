# Claude Code configuration you install yourself

These files complete the AI-assisted development setup, but they live in paths the agent is **not allowed to write** in this project (`.claude/settings.json`, `.claude/hooks/`, `.claude/skills/`). That is deliberate: hooks execute commands and settings control permissions, so they are changes you should make and review yourself.

Everything else is already active in the repo: `CLAUDE.md`, `AGENTS.md`, `.claude/commands/` (`/next-task`, `/verify`, `/spec-sync`, `/plan-task`, `/spec-interview`, `/secret-scan`), `.claude/agents/` (`spec-reviewer`, `security-reviewer`), `scripts/scan_secrets.py`, `.githooks/pre-commit`, and CI.

## Install (about two minutes)

```bash
mkdir -p .claude/hooks .claude/skills/release-check
cp docs/claude-config/hooks/*.sh .claude/hooks/
chmod +x .claude/hooks/*.sh
cp docs/claude-config/skills/release-check/SKILL.md .claude/skills/release-check/SKILL.md
make hooks        # git pre-commit secret scan for this clone
```

Then merge the `hooks` block from [`settings.hooks.example.json`](./settings.hooks.example.json) into `.claude/settings.json` (keep your existing `permissions`), and run `/hooks` in Claude Code to confirm they appear.

| Hook | Event | What it does |
|---|---|---|
| `protect-files.sh` | PreToolUse `Edit\|Write` | Blocks edits to real `.env*` files (the `.env.example` template is allowed), the generated `data/zip_market.json`, and `.git/` |
| `scan-on-commit.sh` | PreToolUse `Bash` | Runs the secret scan before any `git commit` Claude runs; blocks on a finding |
| `format-python.sh` | PostToolUse `Edit\|Write` | Runs `ruff check --fix` and `ruff format` on the edited Python file |
| `stop-gate.sh` (optional) | Stop | Keeps a turn from ending while `make check` fails. Register it under a `"Stop"` key if you want a hard gate for unattended runs |

The scripts need only `bash` and `python3` (no `jq`). Test one: ask Claude to add a line to a `.env` file; the edit should be blocked with a message.

## GitHub Actions with Claude (optional, off by default)

`.github/workflows/claude.yml` (`@claude` mentions) and `claude-review.yml` (advisory PR review) are in the repo but **inert** until you:

1. Install the Claude GitHub App (run `/install-github-app` in Claude Code, or follow <https://code.claude.com/docs/en/github-actions>).
2. Add the repository secret `ANTHROPIC_API_KEY` (or switch the workflows to `claude_code_oauth_token`). Never commit it.
3. Set the repository variable `CLAUDE_ACTION_ENABLED` to `true`.

Costs: each run uses GitHub Actions minutes and API tokens; both workflows set timeouts and turn limits. Only people with write access can trigger `@claude`, and the review skips forks and drafts. Neither is a required check.
