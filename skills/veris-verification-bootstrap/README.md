# Veris Verification Bootstrap v1.2 — Shared Runtime

Portable Bootstrap skill for Claude Code and OpenAI Codex.

## Install

Claude Code:
  .claude/skills/veris-verification-bootstrap/

Codex:
  .agents/skills/veris-verification-bootstrap/

Use this v1.2 folder to replace the existing skill directory.
Do not overwrite project-specific .veris files.

## Modes

bootstrap: discover, configure, verify.
harden: repair gaps, preserve prior evidence, revalidate.
validate: recheck existing setup, write fresh evidence only.

Claude:
  /veris-verification-bootstrap mode=harden

Codex:
  $veris-verification-bootstrap mode=harden

## What is new in v1.2?

A shared runtime interface consumed by Story Verifier and
Regression Runner. It uses a project-specific sandbox contract:

  .veris/sandbox/sandbox.yaml

and the portable Python adapter:

  .veris/sandbox/runtime.py

The first working adapter uses Docker Compose.
VM/cloud adapters are not implemented in this package.

## Scaffold runtime assets

From the repository root, invoke:

  python3 <skill-dir>/scripts/scaffold_runtime.py --root .

This copies demonstration files into .veris/sandbox/.
It never overwrites existing sandbox files.

Then adapt Dockerfile, compose.yaml, and sandbox.yaml for the real app.
The sample is intentionally status=draft; it is not verification-ready.

## Contract format

sandbox.yaml deliberately contains JSON-formatted YAML 1.2.
JSON is a YAML 1.2-compatible subset and can be loaded using
the Python standard library, without a YAML dependency.

Do not rewrite it into free-form YAML unless the adapter is changed
to support a YAML parser.

## Runtime lifecycle

  python3 .veris/sandbox/runtime.py --root . validate

  python3 .veris/sandbox/runtime.py --root . validate --with-docker

  python3 .veris/sandbox/runtime.py --root . build --approved

  python3 .veris/sandbox/runtime.py --root . provision --owner STORY-142

  python3 .veris/sandbox/runtime.py --root . start --instance <id>

  python3 .veris/sandbox/runtime.py --root . healthcheck --instance <id>

  python3 .veris/sandbox/runtime.py --root . execute \
    --instance <id> --argv-file <relative-command.json>

  python3 .veris/sandbox/runtime.py --root . collect --instance <id>

  python3 .veris/sandbox/runtime.py --root . destroy --instance <id>

  python3 .veris/sandbox/runtime.py --root . status --instance <id>

The adapter prevents provisioning from a draft contract.
Images are built only when explicitly approved.
Ordinary test runs use --no-build and --pull never.

An argv file is a JSON list of command arguments.
Do not put credentials in arguments.

## Where things live

Reusable Docker image: Docker image store or registry.
Running containers: configured Docker host.
Runtime definition and adapter: .veris/sandbox/
Instance state and raw evidence: .veris/runtime-instances/
Bootstrap evidence: .veris/evidence/
Story and regression evidence: their own .veris paths.

runtime-instances is gitignored by the scaffold script.
Raw logs may contain sensitive data: review/redact before sharing.

## Limitations

Docker Compose v2 is required for Docker-backed runtime commands.
A working Docker daemon is required for build/start/execute.
The package does not provision cloud VMs or install Docker.
Docker alone is not a complete sandbox for hostile code.

The skill and adapter cannot prove that a container represents the
real application until the application-specific tests are executed.

## Offline helper tests

From this skill's root:
  python3 -m unittest discover -s tests -v

These tests do not need Docker or cloud accounts.

## Handoff contract

Update .veris/verification-profile.yaml so sandbox points to:
  configuration_path: .veris/sandbox/sandbox.yaml
  adapter_path: .veris/sandbox/runtime.py
  provider: docker-compose

Story Verifier and Regression Runner call the same runtime adapter.
Bootstrap owns images and the reusable definition; consumers own
their temporary instances.

## Historical reporting

Retains v1.1:
- .veris/bootstrap-report.md
- .veris/reports/run-NNNN.md
- .veris/evidence/run-NNNN/results.json

Harden/validate compare with previous required checks.

## Security

Do not grant Docker access to untrusted actors.
Do not commit secrets or raw sensitive runtime logs.
Provision only in authorized environments with appropriate budgets.
