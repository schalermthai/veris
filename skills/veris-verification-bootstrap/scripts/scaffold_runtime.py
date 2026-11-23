#!/usr/bin/env python3
"""Copy reusable runtime scaffold into a project without overwriting files."""
import argparse
import json
import shutil
import sys
from pathlib import Path


def scaffold(root, skill_root):
    profile = root / ".veris" / "verification-profile.yaml"
    if not profile.is_file():
        raise ValueError("Create the Veris verification profile before scaffolding")
    base = root / ".veris" / "sandbox"
    source = skill_root / "assets" / "sandbox"
    mapping = {
        "sandbox.yaml": source / "sandbox.yaml",
        "compose.yaml": source / "compose.yaml",
        "Dockerfile": source / "Dockerfile",
        "runtime.py": skill_root / "scripts" / "runtime_adapter.py"
    }
    base.mkdir(parents=True, exist_ok=True)
    created, existing = [], []
    for name, source_path in mapping.items():
        target = base / name
        if target.exists() or target.is_symlink():
            existing.append(str(target.relative_to(root)))
            continue
        with target.open("xb") as output:
            output.write(source_path.read_bytes())
        if name == "runtime.py":
            target.chmod(0o700)
        created.append(str(target.relative_to(root)))
    instance_dir = root / ".veris" / "runtime-instances"
    instance_dir.mkdir(parents=True, exist_ok=True)
    ignore = instance_dir / ".gitignore"
    if not ignore.exists():
        ignore.write_text("*\n!.gitignore\n", encoding="utf-8")
        created.append(str(ignore.relative_to(root)))
    return {
        "created": created,
        "existing_preserved": existing,
        "profile_updates_required": {
            "sandbox.enabled": True,
            "sandbox.provider": "docker-compose",
            "sandbox.configuration_path": ".veris/sandbox/sandbox.yaml",
            "sandbox.adapter_path": ".veris/sandbox/runtime.py"
        },
        "warning": "Sample is draft. Customize, build, verify real flows, and approve before marking ready."
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=".")
    a = p.parse_args()
    root = Path(a.root).resolve()
    if not root.is_dir():
        p.error("Root directory does not exist")
    try:
        result = scaffold(root, Path(__file__).resolve().parent.parent)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError) as error:
        print("Scaffold error: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
