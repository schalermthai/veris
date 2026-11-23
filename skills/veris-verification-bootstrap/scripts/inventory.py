#!/usr/bin/env python3
"""Read-only repository discovery helper; Python standard library."""
import argparse
import json
import os
from pathlib import Path

SKIP = {".git", ".veris", "node_modules", ".venv", "venv",
        "dist", "build", "coverage", ".next", "__pycache__"}
FILES = {"package.json", "pnpm-workspace.yaml", "pyproject.toml",
         "requirements.txt", "uv.lock", "poetry.lock", "Cargo.toml",
         "go.mod", "pom.xml", "build.gradle", "Gemfile", "Dockerfile",
         "compose.yaml", "compose.yml", "docker-compose.yml",
         "Makefile", "justfile", "playwright.config.ts",
         "pytest.ini", "AGENTS.md", "CLAUDE.md", "README.md"}
ENV = {".env.example", ".env.sample", ".env.template"}
TESTDIRS = {"tests", "test", "e2e", "integration", "__tests__"}


def inventory(root):
    result = {"root": str(root), "files": [], "env_examples": [],
              "test_directories": [], "package_scripts": {},
              "warnings": []}
    scanned = 0
    for base, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in SKIP and
                         not (Path(base) / d).is_symlink())
        folder = Path(base)
        if folder.name in TESTDIRS:
            result["test_directories"].append(str(folder.relative_to(root)))
        for name in sorted(names):
            scanned += 1
            if scanned > 50000:
                result["warnings"].append("File scan limit reached")
                break
            path = folder / name
            rel = str(path.relative_to(root))
            if name in FILES:
                result["files"].append(rel)
            if name in ENV:
                result["env_examples"].append(rel)
            if name == "package.json" and not path.is_symlink():
                try:
                    if path.stat().st_size > 2000000:
                        raise ValueError("Oversized manifest")
                    doc = json.loads(path.read_text(encoding="utf-8"))
                    result["package_scripts"][rel] = sorted(
                        doc.get("scripts", {}).keys())
                except (OSError, ValueError, TypeError, AttributeError):
                    result["warnings"].append("Cannot parse " + rel)
        if scanned > 50000:
            break
    result["files_scanned"] = scanned
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    a = parser.parse_args()
    root = Path(a.root).resolve()
    if not root.is_dir():
        parser.error("Repository root does not exist")
    print(json.dumps(inventory(root), indent=2))


if __name__ == "__main__":
    main()
