#!/usr/bin/env python3
"""Veris shared Docker Compose runtime lifecycle.

Python 3.9+ standard library. Docker Compose v2 required for
provider-backed operations. This is a tool adapter, not a substitute
for host isolation, authorization, or sandbox security.

Instance state and raw evidence are stored beneath the project in
.veris/runtime-instances/, which should be gitignored.
"""
import argparse
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import time
from pathlib import Path

ALLOWED_PROVIDERS = {"docker-compose"}
STATES = {"allocated", "started", "start_failed", "destroyed"}
SAFE_ID = re.compile(r"^[a-z][a-z0-9-]{0,30}$")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def within(path, root):
    return path.resolve().is_relative_to(root.resolve())


def project_file(root, name):
    p = Path(name)
    if p.is_absolute():
        raise ValueError("Absolute project paths are not allowed")
    target = root / p
    if not within(target, root):
        raise ValueError("Project path escapes root: " + name)
    return target


def load_contract(root):
    path = root / ".veris" / "sandbox" / "sandbox.yaml"
    config = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or config.get("schema_version") != 1:
        raise ValueError("Invalid sandbox contract schema")
    if config.get("template_status") not in {"draft", "ready"}:
        raise ValueError("template_status must be draft or ready")
    runtime = config.get("runtime")
    if not isinstance(runtime, dict):
        raise ValueError("Missing runtime object")
    if runtime.get("provider") not in ALLOWED_PROVIDERS:
        raise ValueError(
            "Provider unsupported in this adapter: " +
            str(runtime.get("provider")))
    prefix = runtime.get("project_prefix")
    if not isinstance(prefix, str) or not SAFE_ID.fullmatch(prefix):
        raise ValueError("Unsafe Compose project prefix")
    compose = project_file(root, runtime.get("compose_file", ""))
    if not compose.is_file():
        raise ValueError("Missing Compose file: " + str(compose))
    service = runtime.get("exec_service")
    required = runtime.get("required_services")
    if not isinstance(service, str) or not service:
        raise ValueError("Missing exec_service")
    if not isinstance(required, list) or not required or (
        not all(isinstance(x, str) and x for x in required)):
        raise ValueError("Missing required_services")
    if service not in required:
        raise ValueError("exec_service must be a required service")
    limits = runtime.get("limits")
    if not isinstance(limits, dict):
        raise ValueError("Missing limits")
    for key in ("max_parallel_instances", "start_timeout_seconds",
                "execute_timeout_seconds", "destroy_timeout_seconds"):
        val = limits.get(key)
        if not isinstance(val, int) or isinstance(val, bool) or val < 1:
            raise ValueError("Invalid runtime limit: " + key)
    allowed = runtime.get("allowed_executables", [])
    if not isinstance(allowed, list) or not allowed or not all(
        isinstance(x, str) and x and "/" not in x and
        "\\" not in x and not x.startswith("-") for x in allowed):
        raise ValueError("Invalid approved executable list")
    isolation = runtime.get("isolation")
    if not isinstance(isolation, dict) or isolation.get("disposable") is not True:
        raise ValueError("Runtime must declare disposable isolation")
    security = runtime.get("security")
    if not isinstance(security, dict) or security.get("production_access") is not False:
        raise ValueError("Production access must be false")
    images = runtime.get("images", [])
    if not isinstance(images, list):
        raise ValueError("runtime.images must be an array")
    for image in images:
        if not isinstance(image, dict) or not isinstance(image.get("reference"), str):
            raise ValueError("Invalid image entry")
        if image.get("service") not in required:
            raise ValueError("Image service must be in required_services")
    return path, config, compose


def docker_compose(compose, project, arguments):
    return [
        "docker", "compose", "--project-directory", str(compose.parent),
        "-f", str(compose), "-p", project
    ] + list(arguments)


def call(argv, timeout=60):
    try:
        result = subprocess.run(
            argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=timeout, check=False
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        raise RuntimeError("Timed out while running Docker command")
    except FileNotFoundError:
        raise RuntimeError("Docker CLI unavailable")


def compose_model(compose, project):
    rc, output, _ = call(
        docker_compose(compose, project, ["config", "--format", "json"]),
        timeout=30
    )
    if rc != 0:
        raise RuntimeError(
            "docker compose config failed (exit " + str(rc) +
            "); details intentionally withheld to avoid secret leakage")
    model = json.loads(output.decode("utf-8"))
    if not isinstance(model, dict):
        raise ValueError("Docker Compose config did not return an object")
    return model


def review_compose(model, cfg):
    errors = []
    runtime = cfg["runtime"]
    isolation = runtime["isolation"]
    services = model.get("services", {})
    if not isinstance(services, dict):
        return ["No usable services in Compose model"]
    for name in runtime["required_services"]:
        if name not in services:
            errors.append("Missing required service: " + name)
        elif runtime.get("require_healthy", True) and (
            not services[name].get("healthcheck")):
            errors.append("Required service lacks healthcheck: " + name)
    for name, service in services.items():
        if not isinstance(service, dict):
            errors.append("Invalid service: " + name)
            continue
        if service.get("privileged"):
            errors.append(name + ": privileged container not allowed")
        for key in ("pid", "ipc", "network_mode"):
            if service.get(key) == "host":
                errors.append(name + ": host namespace not allowed")
        if service.get("container_name"):
            errors.append(name + ": fixed container_name is forbidden")
        if service.get("devices") or service.get("cap_add"):
            errors.append(name + ": extra devices/capabilities not allowed")
        if service.get("env_file"):
            errors.append(name + ": service env_file requires separate review")
        for mount in service.get("volumes", []):
            if isinstance(mount, dict):
                kind = mount.get("type")
                source = str(mount.get("source", ""))
                if "docker.sock" in source:
                    errors.append(name + ": Docker socket mount forbidden")
                if kind == "bind" and not isolation.get("allow_host_bind_mounts", False):
                    errors.append(name + ": host bind mount forbidden")
            else:
                errors.append(name + ": unsupported volume representation")
        for port in service.get("ports", []):
            if isinstance(port, dict):
                published = port.get("published")
                if published not in (None, "", "0", 0) and not isolation.get(
                    "allow_fixed_host_ports", False):
                    errors.append(name + ": fixed host port forbidden")
            else:
                errors.append(name + ": unsupported port representation")
    for kind in ("networks", "volumes"):
        values = model.get(kind, {})
        if not isinstance(values, dict):
            continue
        for name, settings in values.items():
            if not isinstance(settings, dict):
                continue
            if settings.get("external") and not isolation.get(
                "allow_external_" + kind, False):
                errors.append("External " + kind + " not allowed: " + name)
            if kind == "volumes" and settings.get("name") and not settings.get("external"):
                # Compose produces a canonical name; only clearly
                # shared explicitly named values should be reviewed.
                if not str(settings.get("name")).startswith(model.get("name", "") + "_"):
                    errors.append("Possibly shared named volume: " + name)
    return errors


def require_ready(config):
    if config.get("template_status") != "ready":
        raise ValueError("Runtime template is draft; bootstrap must validate it")


def image_check(config):
    runtime = config["runtime"]
    if not runtime.get("enforce_image_identity", False):
        return {"enforced": False, "images": []}
    images = runtime.get("images", [])
    services = set(runtime["required_services"])
    if {x["service"] for x in images} != services:
        raise ValueError("All required services need pinned image entries")
    results = []
    for item in images:
        reference = item["reference"]
        expected = item.get("expected_local_id")
        if not expected and "@sha256:" not in reference:
            raise ValueError("Missing pinned image identity: " + reference)
        rc, raw, _ = call(
            ["docker", "image", "inspect", "--format", "{{.Id}}", reference],
            timeout=30
        )
        if rc != 0:
            raise RuntimeError("Cannot inspect required image reference")
        actual = raw.decode("utf-8", "replace").strip()
        if expected and actual != expected:
            raise ValueError("Image identity mismatch: " + reference)
        results.append({"reference": reference, "local_id": actual})
    return {"enforced": True, "images": results}


def instance_root(root):
    return root / ".veris" / "runtime-instances"


def lock(root):
    directory = instance_root(root) / ".lock"
    try:
        directory.mkdir()
    except FileExistsError:
        raise RuntimeError(
            "Runtime allocation lock exists; inspect for active operation")
    return directory


def state_path(root, instance):
    if not isinstance(instance, str) or not SAFE_ID.fullmatch(instance):
        raise ValueError("Unsafe instance ID")
    folder = instance_root(root) / instance
    if not within(folder, instance_root(root)):
        raise ValueError("Invalid instance path")
    return folder / "state.json"


def read_state(root, instance):
    path = state_path(root, instance)
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("instance") != instance or data.get("state") not in STATES:
        raise ValueError("Invalid instance state")
    return path, data


def write_json(path, data):
    temp = path.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)
        file.write("\n")
    temp.chmod(0o600)
    os.replace(temp, path)


def check_drift(config_path, compose, state):
    if (state.get("contract_sha256") != sha(config_path)
        or state.get("compose_sha256") != sha(compose)):
        raise ValueError(
            "Runtime definition changed while instance existed. "
            "Use original configuration or manual recovery; no automatic cleanup.")


def parse_ps(raw):
    text = raw.decode("utf-8", "replace").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return [parsed]
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def create_state(root, config_path, config, compose, owner, revision):
    require_ready(config)
    if not isinstance(owner, str) or len(owner) > 120:
        raise ValueError("Invalid owner label")
    instances = instance_root(root)
    instances.mkdir(parents=True, exist_ok=True)
    gate = lock(root)
    try:
        active = 0
        for path in instances.glob("*/state.json"):
            try:
                item = json.loads(path.read_text(encoding="utf-8"))
                if item.get("state") != "destroyed":
                    active += 1
            except (OSError, ValueError):
                active += 1
        if active >= config["runtime"]["limits"]["max_parallel_instances"]:
            raise ValueError("Max active runtime instances reached")
        instance = config["runtime"]["project_prefix"] + "-" + secrets.token_hex(5)
        path = state_path(root, instance)
        path.parent.mkdir(mode=0o700, exist_ok=False)
        (path.parent / "evidence").mkdir(mode=0o700)
        data = {
            "schema_version": 1,
            "instance": instance,
            "state": "allocated",
            "owner": owner,
            "revision": revision,
            "contract_sha256": sha(config_path),
            "compose_sha256": sha(compose),
            "created_at_epoch": int(time.time()),
            "execution_count": 0
        }
        write_json(path, data)
        return data
    finally:
        gate.rmdir()


def save_raw(path, data):
    with path.open("wb") as file:
        file.write(data)
    path.chmod(0o600)


def cmd_validate(root, config_path, config, compose, with_docker):
    result = {"valid": True, "provider": config["runtime"]["provider"],
              "template_status": config["template_status"],
              "compose_file": str(compose.relative_to(root)),
              "docker_checked": False, "errors": []}
    if with_docker:
        model = compose_model(compose, config["runtime"]["project_prefix"] + "-review")
        errors = review_compose(model, config)
        result["docker_checked"] = True
        result["errors"] = errors
        result["valid"] = not errors
    return result


def cmd_build(root, config, compose, approved):
    if not approved:
        raise ValueError("Building images requires --approved")
    model = compose_model(compose, config["runtime"]["project_prefix"] + "-build")
    errors = review_compose(model, config)
    if errors:
        raise ValueError("Unsafe Compose configuration: " + "; ".join(errors))
    project = config["runtime"]["project_prefix"] + "-build"
    rc, _, _ = call(
        docker_compose(compose, project, ["build"]),
        timeout=1800
    )
    if rc != 0:
        raise RuntimeError("Image build failed (exit " + str(rc) + ")")
    return {"build_succeeded": True,
            "note": "Record image IDs/digests and validate actual app before setting template ready"}


def cmd_start(root, path, config_path, config, compose, instance):
    require_ready(config)
    state_file, state = read_state(root, instance)
    check_drift(config_path, compose, state)
    if state["state"] == "destroyed":
        raise ValueError("Instance was already destroyed")
    image_check(config)
    model = compose_model(compose, instance)
    errors = review_compose(model, config)
    if errors:
        raise ValueError("Compose review failed: " + "; ".join(errors))
    timeout = config["runtime"]["limits"]["start_timeout_seconds"]
    rc, _, _ = call(
        docker_compose(compose, instance, [
            "up", "--no-build", "--pull", "never",
            "--wait", "--wait-timeout", str(timeout)
        ]),
        timeout=timeout + 40
    )
    state["state"] = "started" if rc == 0 else "start_failed"
    write_json(state_file, state)
    if rc:
        raise RuntimeError("Compose startup failed (exit " + str(rc) + ")")
    return {"instance": instance, "started": True}


def cmd_health(root, config, compose, instance):
    state_file, state = read_state(root, instance)
    if state["state"] != "started":
        raise ValueError("Instance not started")
    rc, raw, _ = call(
        docker_compose(compose, instance, ["ps", "--all", "--format", "json"]),
        timeout=30
    )
    if rc != 0:
        raise RuntimeError("Could not inspect Compose containers")
    rows = parse_ps(raw)
    statuses = {x.get("Service"): {"state": x.get("State"),
                                  "health": x.get("Health", "")}
                for x in rows if isinstance(x, dict)}
    errors = []
    for service in config["runtime"]["required_services"]:
        actual = statuses.get(service)
        if not actual or actual["state"] != "running":
            errors.append(service + ": not running")
        elif config["runtime"].get("require_healthy", True) and (
            actual["health"] != "healthy"):
            errors.append(service + ": not healthy")
    return {"healthy": not errors, "services": statuses,
            "errors": errors}


def cmd_execute(root, config, compose, instance, argv_path):
    state_file, state = read_state(root, instance)
    if state["state"] != "started":
        raise ValueError("Cannot execute; instance not started")
    argv_file = project_file(root, argv_path)
    argv = json.loads(argv_file.read_text(encoding="utf-8"))
    if not isinstance(argv, list) or not argv or not all(
        isinstance(s, str) and s and "\x00" not in s for s in argv):
        raise ValueError("argv file must be a nonempty string array")
    if argv[0] not in config["runtime"]["allowed_executables"]:
        raise ValueError("Executable is not approved by runtime contract")
    rc, output, error = call(
        docker_compose(compose, instance, [
            "exec", "-T", config["runtime"]["exec_service"]
        ] + argv),
        timeout=config["runtime"]["limits"]["execute_timeout_seconds"]
    )
    state["execution_count"] += 1
    number = state["execution_count"]
    evidence = state_file.parent / "evidence"
    outpath = evidence / ("exec-%04d.stdout.txt" % number)
    errpath = evidence / ("exec-%04d.stderr.txt" % number)
    save_raw(outpath, output)
    save_raw(errpath, error)
    write_json(state_file, state)
    return {
        "instance": instance, "exit_code": rc,
        "stdout_file": str(outpath.relative_to(root)),
        "stderr_file": str(errpath.relative_to(root)),
        "warning": "Raw output may contain sensitive information"
    }


def cmd_collect(root, compose, instance, tail):
    state_file, state = read_state(root, instance)
    if state["state"] == "destroyed":
        raise ValueError("Instance is destroyed")
    rc, logs, _ = call(
        docker_compose(compose, instance, [
            "logs", "--no-color", "--timestamps", "--tail", str(tail)
        ]), timeout=60)
    if rc != 0:
        raise RuntimeError("Log collection failed")
    evidence = state_file.parent / "evidence"
    destination = evidence / "compose-logs.txt"
    if destination.exists():
        destination = evidence / ("compose-logs-%d.txt" % int(time.time()))
    save_raw(destination, logs)
    return {
        "logs": str(destination.relative_to(root)),
        "warning": "Treat logs as potentially sensitive; redact before sharing"
    }


def cmd_destroy(root, compose, config, instance):
    state_file, state = read_state(root, instance)
    if state["state"] == "destroyed":
        return {"instance": instance, "already_destroyed": True}
    rc, _, _ = call(
        docker_compose(compose, instance, [
            "down", "--volumes", "--remove-orphans",
            "--timeout", str(min(60, config["runtime"]["limits"]["destroy_timeout_seconds"]))
        ]), timeout=config["runtime"]["limits"]["destroy_timeout_seconds"] + 30
    )
    if rc != 0:
        raise RuntimeError("Instance teardown failed (exit " + str(rc) + ")")
    state["state"] = "destroyed"
    state["destroyed_at_epoch"] = int(time.time())
    write_json(state_file, state)
    return {"instance": instance, "destroyed": True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    actions = parser.add_subparsers(dest="action", required=True)
    validate = actions.add_parser("validate")
    validate.add_argument("--with-docker", action="store_true")
    build = actions.add_parser("build")
    build.add_argument("--approved", action="store_true")
    provision = actions.add_parser("provision")
    provision.add_argument("--owner", required=True)
    provision.add_argument("--revision")
    for name in ("start", "healthcheck", "status", "collect", "destroy", "execute"):
        sub = actions.add_parser(name)
        sub.add_argument("--instance", required=True)
        if name == "execute":
            sub.add_argument("--argv-file", required=True)
        if name == "collect":
            sub.add_argument("--tail", type=int, default=500)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    try:
        if not root.is_dir():
            raise ValueError("Project root does not exist")
        config_path, cfg, compose = load_contract(root)
        action = args.action
        if action == "validate":
            result = cmd_validate(root, config_path, cfg, compose, args.with_docker)
        elif action == "build":
            result = cmd_build(root, cfg, compose, args.approved)
        elif action == "provision":
            result = create_state(
                root, config_path, cfg, compose, args.owner, args.revision)
        else:
            state_file, state = read_state(root, args.instance)
            if action not in {"status"}:
                check_drift(config_path, compose, state)
            if action == "status":
                result = state
            elif action == "start":
                result = cmd_start(root, state_file, config_path, cfg,
                                   compose, args.instance)
            elif action == "healthcheck":
                result = cmd_health(root, cfg, compose, args.instance)
            elif action == "execute":
                result = cmd_execute(root, cfg, compose, args.instance,
                                     args.argv_file)
            elif action == "collect":
                result = cmd_collect(root, compose, args.instance, args.tail)
            elif action == "destroy":
                result = cmd_destroy(root, compose, cfg, args.instance)
        print(json.dumps(result, indent=2))
        if action == "validate" and not result.get("valid", False):
            return 1
        if action == "healthcheck" and not result.get("healthy", False):
            return 1
        if action == "execute" and result["exit_code"] != 0:
            return 1
        return 0
    except (OSError, ValueError, RuntimeError, TypeError, KeyError,
            json.JSONDecodeError) as error:
        print("Runtime error: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
