# Veris Regression Selector v1.0 — Jev Edition

Skill 04 of 6, portable across Claude Code and OpenAI Codex.

## Install

Claude Code:
  .claude/skills/veris-regression-selector/

Codex:
  .agents/skills/veris-regression-selector/

## Invoke

Claude:
  /veris-regression-selector mode=select

Codex:
  $veris-regression-selector mode=select

Both tools can run the bundled Python helpers.
The skill uses existing .veris project and regression metadata.

## Requirements

Python 3.9+ standard library.
Git.
Prior skill veris-regression-author generated:
  .veris/regression/catalog.json

Optional Jev API:
  TYPESAFE_API_KEY
  POST https://api.typesafe.ai/v1/systemone

No Jev SDK is required for the REST adapter.
Jev is optional; Claude/Codex semantic review is a fallback.

## Commands

Inventory catalog:
  python3 scripts/inspect_catalog.py --root .

Capture change:
  python3 scripts/collect_changes.py --root . \
    --base origin/main --head HEAD --change-id PR-184 \
    --out .veris/regression/selections/PR-184/runs/run-0001/changes.json

Jev preview (NO network):
  python3 scripts/classify_with_jev.py \
    --input safe-jev-input.json --dry-run

Jev live (requires explicit authorization before running):
  python3 scripts/classify_with_jev.py \
    --input safe-jev-input.json --output impact.json \
    --allow-network --context-approved

Create selection:
  python3 scripts/build_selection.py --root . \
    --changes changes.json --impact impact.json --out selection.json

Validate:
  python3 scripts/validate_selection.py --root . \
    --selection selection.json

Compare:
  python3 scripts/compare_selections.py old.json new.json

## Security

The Jev adapter sends only the supplied allowlisted summary and
case metadata; it does not automatically read or send the entire
Git diff. Inspect the dry-run payload before authorizing it.

Set TYPESAFE_API_KEY securely. Never commit API keys.
No external model can override mandatory test policy.

## Important selection semantics

All cataloged cases must be accounted for.
Unclassified/unknown cases are selected conservatively.
Jev output is NOT sufficient to exclude a test.
Only coding-agent-reviewed unrelated cases can be excluded.
An invalid catalog blocks selection.

## Outputs

Manifest:
  selection.json

Report:
  selection-report.md

Provenance:
  Git revisions, diff SHA256, catalog SHA256, policy SHA256

Tests are NOT executed by this skill.

## Helper tests

From skill root:
  python3 -m unittest discover -s tests -v

The tests use local fixtures; no API key or network needed.

## Next

Pass a validated selection.json to veris-regression-runner.
