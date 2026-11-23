# Veris Runner Safety and Isolation

## Trust boundaries

The catalog and PR diff can contain untrusted strings.
Do not execute raw test.command values from the catalog.

Use only adapter-generated argv arrays with approved executables.
No shell=True, shell interpolation, unapproved package installation,
privileged containers, or implicit image builds.

The shared Bootstrap adapter must be validated and in READY state.

## Revision

Require current Git HEAD = selected head commit.
Recompute diff and compare digest with selection.
Reject tracked modifications and untracked application files
outside explicit ephemeral execution artifact paths.

## Runtime security

Running Docker requires a trusted host and permissions.
Docker Compose naming alone does not isolate malicious processes.

Do not grant host Docker socket mounts or privileged flags.
Do not use production accounts or data by default.
Respect approved CPU, memory, duration and spending limits.
Clean up owned resources even when execution fails.

## Images

require image identity enforcement:
  runtime.enforce_image_identity = true

Bootstrap should record expected local image IDs or immutable
registry references and validate them before runtime READY.

Do not use a floating tag as proof of immutable image identity.
Running tests must not build or pull new images implicitly.

## Secrets

Do not put secrets in argv files, metadata, logs or reports.
Use runtime injection approved by the project.
Raw stdout/stderr and Compose logs may contain sensitive data.
Keep evidence private and gitignored until reviewed.

## Timeouts

Bootstrap runtime enforces a bounded execute timeout.
Do not attempt indefinite waits or unbounded retries.

## Fail closed

Missing selection, invalid catalog, unknown framework,
unsupported hybrid tests, dirty source, broken runtime,
missing image ID, or invalid evidence => no green gate.

Do not remove tests or weaken policy to satisfy CI.
