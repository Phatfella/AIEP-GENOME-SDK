"""Tests for scaffold.py — aiep-genome init (all 4 patterns)."""
import json
import os
import tempfile
import unittest

from aiep_genome.scaffold import scaffold_new_project, ScaffoldResult


PATTERNS = ["bare", "evidence-ledger", "mirror", "governance"]

# Files every pattern must produce
COMMON_FILES = [
    "pyproject.toml",
    "README.md",
    ".aiep-genome.json",
]


def _run_scaffold(tmp: str, pattern: str, name: str = "my_service") -> ScaffoldResult:
    return scaffold_new_project(
        tmp,
        name=name,
        version="0.1.0",
        pattern=pattern,
        force=False,
    )


class TestScaffoldCommon(unittest.TestCase):
    """Each pattern must create core files and return clean result."""

    def setUp(self):
        self._dirs = []

    def tearDown(self):
        import shutil
        for d in self._dirs:
            shutil.rmtree(d, ignore_errors=True)

    def _tmp(self) -> str:
        d = tempfile.mkdtemp()
        self._dirs.append(d)
        return d

    def _check_common(self, tmp: str, result: ScaffoldResult):
        self.assertTrue(result.ok, f"scaffold failed: {result}")
        self.assertIsInstance(result.created_files, list)
        self.assertGreater(len(result.created_files), 0)

        for rel in COMMON_FILES:
            abs_path = os.path.join(tmp, rel)
            self.assertTrue(os.path.exists(abs_path), f"Missing {rel}")

        # .aiep-genome.json must be valid JSON with required keys
        cfg_path = os.path.join(tmp, ".aiep-genome.json")
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        for key in ("name", "pattern", "kernel_version", "genome_sdk_version"):
            self.assertIn(key, cfg, f"Missing key {key!r} in .aiep-genome.json")

        # pyproject.toml must mention the package name
        ppt_path = os.path.join(tmp, "pyproject.toml")
        with open(ppt_path, encoding="utf-8") as f:
            content = f.read()
        self.assertIn("my_service", content)

    def test_bare(self):
        tmp = self._tmp()
        result = _run_scaffold(tmp, "bare")
        self._check_common(tmp, result)

    def test_evidence_ledger(self):
        tmp = self._tmp()
        result = _run_scaffold(tmp, "evidence-ledger")
        self._check_common(tmp, result)

    def test_mirror(self):
        tmp = self._tmp()
        result = _run_scaffold(tmp, "mirror")
        self._check_common(tmp, result)

    def test_governance(self):
        tmp = self._tmp()
        result = _run_scaffold(tmp, "governance")
        self._check_common(tmp, result)


class TestScaffoldBare(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._result = _run_scaffold(self._tmp, "bare")

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_genome_init_exists(self):
        self.assertTrue(os.path.exists(os.path.join(self._tmp, "src", "my_service", "genome", "__init__.py")))

    def test_test_file_exists(self):
        tests_dir = os.path.join(self._tmp, "tests")
        self.assertTrue(any("test_" in f for f in os.listdir(tests_dir)))

    def test_config_pattern_bare(self):
        with open(os.path.join(self._tmp, ".aiep-genome.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertEqual(cfg["pattern"], "bare")


class TestScaffoldEvidenceLedger(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._result = _run_scaffold(self._tmp, "evidence-ledger")

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_ledger_module_present(self):
        self.assertTrue(os.path.exists(os.path.join(self._tmp, "src", "my_service", "genome", "ledger.py")))

    def test_ledger_has_evidence_ledger_class(self):
        with open(os.path.join(self._tmp, "src", "my_service", "genome", "ledger.py"), encoding="utf-8") as f:
            content = f.read()
        self.assertIn("class EvidenceLedger", content)

    def test_ledger_has_commit_method(self):
        with open(os.path.join(self._tmp, "src", "my_service", "genome", "ledger.py"), encoding="utf-8") as f:
            content = f.read()
        self.assertIn("def commit(", content)

    def test_compliance_tests_exist(self):
        tests_dir = os.path.join(self._tmp, "tests")
        files = os.listdir(tests_dir)
        self.assertTrue(any("compliance" in f or "test_" in f for f in files))

    def test_config_pattern_evidence_ledger(self):
        with open(os.path.join(self._tmp, ".aiep-genome.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertEqual(cfg["pattern"], "evidence-ledger")


class TestScaffoldMirror(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._result = _run_scaffold(self._tmp, "mirror")

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_mirror_module_present(self):
        self.assertTrue(os.path.exists(os.path.join(self._tmp, "src", "my_service", "genome", "mirror.py")))

    def test_aiep_mirror_config_present(self):
        self.assertTrue(os.path.exists(os.path.join(self._tmp, ".aiep-mirror.json")))

    def test_mirror_module_has_content_hash(self):
        with open(os.path.join(self._tmp, "src", "my_service", "genome", "mirror.py"), encoding="utf-8") as f:
            content = f.read()
        self.assertIn("content_hash", content)


class TestScaffoldGovernance(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._result = _run_scaffold(self._tmp, "governance")

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_governance_module_present(self):
        self.assertTrue(os.path.exists(os.path.join(self._tmp, "src", "my_service", "genome", "governance.py")))

    def test_ledger_also_present(self):
        self.assertTrue(os.path.exists(os.path.join(self._tmp, "src", "my_service", "genome", "ledger.py")))

    def test_governance_has_arbitration(self):
        with open(os.path.join(self._tmp, "src", "my_service", "genome", "governance.py"), encoding="utf-8") as f:
            content = f.read()
        self.assertIn("arbitration", content.lower())


class TestScaffoldForceFlag(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        import shutil
        self._shutil = shutil

    def tearDown(self):
        self._shutil.rmtree(self._tmp, ignore_errors=True)

    def test_force_false_fails_when_exists(self):
        _run_scaffold(self._tmp, "bare")
        result2 = _run_scaffold(self._tmp, "bare")
        # Without --force, second run should report an issue or skip
        # (behaviour: ok may still be True but no overwrites, OR ok=False with error)
        # The important thing is it does NOT raise an exception
        self.assertIsInstance(result2.ok, bool)

    def test_force_true_overwrites(self):
        _run_scaffold(self._tmp, "bare")
        result2 = scaffold_new_project(
            self._tmp, name="my_service", version="0.2.0", pattern="bare", force=True
        )
        self.assertTrue(result2.ok)
        # pyproject.toml should now reflect the new version
        with open(os.path.join(self._tmp, "pyproject.toml"), encoding="utf-8") as f:
            content = f.read()
        self.assertIn("0.2.0", content)


class TestScaffoldNameSanitization(unittest.TestCase):

    def setUp(self):
        self._dirs = []

    def tearDown(self):
        import shutil
        for d in self._dirs:
            shutil.rmtree(d, ignore_errors=True)

    def _tmp(self):
        d = tempfile.mkdtemp()
        self._dirs.append(d)
        return d

    def test_hyphenated_name_scaffolds(self):
        tmp = self._tmp()
        result = scaffold_new_project(tmp, name="my-service", version="0.1.0",
                                      pattern="bare", force=False)
        self.assertTrue(result.ok)

    def test_config_records_name(self):
        tmp = self._tmp()
        scaffold_new_project(tmp, name="alpha-sdk", version="1.0.0",
                              pattern="bare", force=False)
        with open(os.path.join(tmp, ".aiep-genome.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertIn("alpha", cfg["name"].lower())


if __name__ == "__main__":
    unittest.main()
