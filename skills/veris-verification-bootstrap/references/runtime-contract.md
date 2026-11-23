# Veris Shared Runtime Contract v1

## Separation

Definition:
  .veris/sandbox/sandbox.yaml
  .veris/sandbox/compose.yaml
  .veris/sandbox/Dockerfile
  .veris/sandbox/runtime.py

Image:
  Docker image store or image registry (not in Git).

Disposable instances:
  Running containers in an authorized Docker host.

Instance records:
  .veris/runtime-instances/<id>/state.json

Instance evidence:
  .veris/runtime-instances/<id>/evidence/

Profile pointer:
  .veris/verification-profile.yaml
  sandbox.configuration_path
  sandbox.adapter_path

## Machine format

sandbox.yaml uses JSON syntax, which is compatible with YAML 1.2.
This permits standard-library Python parsing without an extra dependency.

Fields:
- schema_version: 1
- template_status: draft | ready
- runtime.provider: docker-compose
- runtime.compose_file: relative path
- runtime.project_prefix: valid Compose name prefix
- runtime.exec_service: service name for commands
- runtime.required_services: services to verify
- runtime.images: service/image references and expected local IDs
- runtime.enforce_image_identity: boolean
- runtime.require_healthy: boolean
- runtime.allowed_executables: bounded command program list
- runtime.limits: parallelism and timeouts
- runtime.isolation: restrictions on host mounts/external resources
- runtime.security: production and secret policies

No passwords or secret values may appear in contract files.

## Lifecycle commands

validate:
  Check schema and project paths. With --with-docker also call
  docker compose config --format json and inspect risky settings.

build:
  Explicit authorized docker compose build. May update global
  Docker image store. Record image ID; do not claim ready yet.

provision:
  Allocate a unique, project-scoped Compose name and state record.
  Requires template_status=ready. No image build.

start:
  docker compose up --no-build --pull never --wait.
  Requires approved ready definition and image identity policy.

healthcheck:
  Inspect docker compose ps --all --format json.
  Check required services, running state, and healthy state.

execute:
  docker compose exec -T SERVICE COMMAND ARGS without a host shell.
  Read arguments from reviewed JSON argv file.
  Require program allowlist and bounded timeout.

collect:
  Save Compose logs and status to restricted instance evidence.
  Raw logs may contain secrets: do not commit/share unreviewed.

destroy:
  docker compose down --volumes --remove-orphans for the exact
  generated project name. Preserve state and result history.

## Runtime ownership

Bootstrap:
- Configure, build, pin, validate, and harden reusable template.

Story Verifier / Regression Runner:
- Provision, start, healthcheck, execute, collect, destroy
  their own temporary instances.

Consumers must clean up in finally/failure paths.

## Security boundaries

Docker Compose project names reduce accidental collisions but
do not create a security boundary against hostile containers.

By default reject:
- privileged containers
- host networking and host PID/IPC
- Docker socket mounts
- host bind mounts
- external named volumes and networks
- fixed host ports
- custom container_name
- device passthrough and extra capabilities

Bootstrap may propose alternate infrastructure with documented
approvals where real application needs cannot fit these controls.

Do not run unsafe commands merely because .veris contains them.
The adapter's executable allowlist is a guardrail, not a secure
substitute for sandboxing and host authorization.

## Image identity

For local Docker image:
  Record image reference and docker image inspect .Id.
  This is a host-local content identifier.

For registry image:
  Prefer a reference pinned by manifest digest.
  Docker image ID is not identical to a registry manifest digest.

Do not claim a mutable image tag guarantees reproducibility.
On provision/start, check configured image identities.

## Runtime drift

A live instance records contract and Compose SHA256 hashes.
Changing runtime configuration while an instance is active
must not silently change its execution environment.

Create a new instance after template changes.
If cleanup is blocked by drift, keep records and use manual
provider-specific recovery; do not destroy unrelated projects.

## Providers

Implemented: docker-compose
Unsupported in this package: cloud-vm, remote-sandbox, kubernetes

An unsupported provider must fail explicitly.
Future adapters should preserve the same lifecycle semantics.

## Build sample

The bundled Dockerfile/Compose run a simple Python HTTP server
to demonstrate adapter integration ONLY.

They are not project-specific verification containers.
Bootstrap must replace them with actual application tooling,
real services, correct images and real E2E proof.
