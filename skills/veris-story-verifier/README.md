# Veris Story Verifier v1.0

Portable story-level verification skill for Claude Code and Codex.
Consumes the project-specific .veris context produced by
veris-verification-bootstrap v1.1.

## Install

Claude Code:
  <repository>/.claude/skills/veris-story-verifier/

Codex:
  <repository>/.agents/skills/veris-story-verifier/

Keep one canonical copy and symlink into both locations if desired.

## Invoke

Claude Code:
  /veris-story-verifier mode=targeted
  /veris-story-verifier mode=retest
  /veris-story-verifier mode=final

Codex:
  $veris-story-verifier mode=targeted
  $veris-story-verifier mode=retest
  $veris-story-verifier mode=final

These are natural language skill arguments, not shell flags.

## What the skill does

- Loads the project verification profile, playbook and bootstrap report.
- Maps acceptance criteria to specific user-facing scenarios.
- Performs Setup -> Driver -> Checker verification.
- Produces defect reports and recorded evidence.
- Preserves story-specific run history.
- Compares retests without mislabeling unexecuted checks as regressions.
- Suggests candidates for permanent regression tests.

The skill does NOT edit feature code, rebuild the bootstrap environment,
or create permanent E2E regression scripts.

## Scripts

All four scripts use the Python 3.9+ standard library only.

1. check_context.py
   python3 scripts/check_context.py --root .

2. init_run.py
   python3 scripts/init_run.py --root . --story STORY-142 \
     --mode final \
     --ac 'AC-1=Owner initiates transfer' \
     --ac 'AC-2=Recipient accepts transfer'

   Creates a unique run directory and initializes the report/results.

3. validate_results.py
   python3 scripts/validate_results.py \
     .veris/stories/STORY-142/runs/run-0001/results.json

   Optional: --expected-revision <revision>

4. compare_runs.py
   python3 scripts/compare_runs.py \
     .veris/stories/STORY-142/runs/run-0001/results.json \
     .veris/stories/STORY-142/runs/run-0002/results.json

## Output

.veris/stories/<story-id>/
  latest-report.md
  runs/
    run-0001/
      verification-plan.md
      verification-report.md
      results.json
      evidence/

Run IDs are allocated without overwriting existing directories.

The verifier writes supporting evidence into evidence/ and updates
scenario result records before invoking validate_results.py.

## Result schema

criteria:
  id, description, required

scenarios:
  id, criterion_ids, name, required, status, expected,
  actual, independent_check, evidence, defects

Allowed scenario status:
  pass, fail, blocked, inconclusive, not_run

Allowed verdict:
  verified, failed, partial, blocked

Defect status:
  open, fixed, wontfix

An open blocking defect prevents VERIFIED.

PASS requires an actual observation, a passing independent check,
and an existing nonempty evidence artifact.

The validator checks records and artifacts. It cannot establish
that the evidence really proves the software behaves correctly.

## Test the scripts

From the skill directory:
  python3 -m unittest discover -s tests -v

The tests use temporary directories and do not need a real app.

## Initial project requirement

Run veris-verification-bootstrap first.
If .veris/verification-profile.yaml and the playbook are absent,
init_run.py will stop rather than invent a verification environment.

## Revisions and dirty worktrees

init_run.py records the Git HEAD when available and detects whether
the worktree was dirty at run initialization.

A commit hash alone does not identify uncommitted code changes.
For high-assurance testing, use immutable checkouts or a separately
recorded worktree snapshot. The validator cannot prove that no files
changed while browser verification was happening.

## Security

Never store secrets in test evidence. Use disposable accounts and
approved sandboxes. Do not infer authorization from .veris commands.

## Next in the suite

veris-regression-author turns successfully verified behavior into
reusable hybrid E2E regression tests.
