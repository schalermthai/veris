"""Offline tests for runtime contract and adapter. No Docker required."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "veris_runtime", ROOT / "scripts" / "runtime_adapter.py")
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)

SCAFFOLD_SPEC = importlib.util.spec_from_file_location(
    "veris_scaffold", ROOT / "scripts" / "scaffold_runtime.py")
scaffold = importlib.util.module_from_spec(SCAFFOLD_SPEC)
SCAFFOLD_SPEC.loader.exec_module(scaffold)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / ".veris").mkdir()
        (self.root / ".veris" / "verification-profile.yaml").write_text(
            "schema_version: 1\nsandbox:\n  enabled: false\n",
            encoding="utf-8"
        )
        self.scaffold = scaffold.scaffold(self.root, ROOT)

    def test_scaffold_creates_assets(self):
        self.assertTrue(
            (self.root / ".veris" / "sandbox" / "sandbox.yaml").is_file())
        self.assertTrue(
            (self.root / ".veris" / "sandbox" / "runtime.py").is_file())

    def test_scaffold_does_not_overwrite(self):
        result = scaffold.scaffold(self.root, ROOT)
        self.assertFalse(result["created"])
        self.assertGreaterEqual(len(result["existing_preserved"]), 4)

    def test_contract_loads_in_draft(self):
        path, cfg, compose = runtime.load_contract(self.root)
        self.assertEqual(cfg["template_status"], "draft")
        self.assertTrue(compose.is_file())

    def test_draft_cannot_provision(self):
        _, cfg, _ = runtime.load_contract(self.root)
        with self.assertRaises(ValueError):
            runtime.require_ready(cfg)

    def test_unsafe_privileged_service_rejected(self):
        _, cfg, _ = runtime.load_contract(self.root)
        model = {
            "name": "veris-review",
            "services": {
                "app": {
                    "privileged": True,
                    "healthcheck": {"test": ["CMD", "true"]}
                }
            }
        }
        errors = runtime.review_compose(model, cfg)
        self.assertTrue(any("privileged" in x for x in errors))

    def test_host_socket_rejected(self):
        _, cfg, _ = runtime.load_contract(self.root)
        model = {
            "name": "veris-review",
            "services": {
                "app": {
                    "healthcheck": {"test": ["CMD", "true"]},
                    "volumes": [{
                        "type": "bind",
                        "source": "/var/run/docker.sock",
                        "target": "/var/run/docker.sock"
                    }]
                }
            }
        }
        errors = runtime.review_compose(model, cfg)
        self.assertTrue(any("socket" in x for x in errors))

    def test_compose_command_has_unique_project(self):
        path = self.root / ".veris" / "sandbox" / "compose.yaml"
        command = runtime.docker_compose(path, "veris-abc123", ["ps"])
        self.assertIn("veris-abc123", command)
        self.assertEqual(command[-1], "ps")

    def test_state_id_rejects_traversal(self):
        with self.assertRaises(ValueError):
            runtime.state_path(self.root, "../other")

    def test_parse_ps_json_lines(self):
        value = (
            b'{"Service":"app","State":"running","Health":"healthy"}\n'
            b'{"Service":"db","State":"running","Health":"healthy"}\n'
        )
        rows = runtime.parse_ps(value)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["Service"], "app")


if __name__ == "__main__":
    unittest.main()
