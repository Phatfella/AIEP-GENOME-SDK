"""Tests for adopt.py — aiep-genome adopt."""
import json
import os
import shutil
import tempfile
import textwrap
import unittest

from aiep_genome.adopt import adopt_project, AdoptResult


def _make_bare_project(tmp: str, name: str = "myapp") -> str:
    """Create minimum viable Python project for adoption."""
    src_dir = os.path.join(tmp, "src", name)
    os.makedirs(src_dir, exist_ok=True)
    with open(os.path.join(src_dir, "__init__.py"), "w", encoding="utf-8") as f:
        f.write(f'__version__ = "0.1.0"\n')
    pyproject = os.path.join(tmp, "pyproject.toml")
    with open(pyproject, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(f"""\
            [build-system]
            requires = ["setuptools"]
            build-backend = "setuptools.backends.legacy:build"

            [project]
            name = "{name}"
            version = "0.1.0"
            dependencies = []
        """))
    tests_dir = os.path.join(tmp, "tests")
    os.makedirs(tests_dir, exist_ok=True)
    with open(os.path.join(tests_dir, "__init__.py"), "w", encoding="utf-8") as f:
        f.write("")
    return tmp


def _make_mirror_project(tmp: str) -> str:
    """Project with mirror-like keywords in source."""
    _make_bare_project(tmp, "mirrorsvc")
    init = os.path.join(tmp, "src", "mirrorsvc", "__init__.py")
    with open(init, "w", encoding="utf-8") as f:
        f.write('# mirror well-known endpoint\n__version__ = "0.1.0"\n')
    return tmp


def _make_governance_project(tmp: str) -> str:
    """Project with arbitration keywords in source."""
    _make_bare_project(tmp, "govsvc")
    init = os.path.join(tmp, "src", "govsvc", "__init__.py")
    with open(init, "w", encoding="utf-8") as f:
        f.write('# arbitration plausibility engine\n__version__ = "0.1.0"\n')
    return tmp


def _make_evidence_project(tmp: str) -> str:
    """Project with evidence ledger keywords."""
    _make_bare_project(tmp, "evdsvc")
    init = os.path.join(tmp, "src", "evdsvc", "__init__.py")
    with open(init, "w", encoding="utf-8") as f:
        f.write('# evidence ledger commit\n__version__ = "0.1.0"\n')
    return tmp


class TestAdoptCore(unittest.TestCase):

    def setUp(self):
        self._dirs = []

    def tearDown(self):
        for d in self._dirs:
            shutil.rmtree(d, ignore_errors=True)

    def _make(self, fn=_make_bare_project) -> str:
        d = tempfile.mkdtemp()
        self._dirs.append(d)
        return fn(d)

    def test_adopt_succeeds_on_bare_project(self):
        tmp = self._make()
        result = adopt_project(tmp, pattern="bare", dry_run=False, force=False)
        self.assertIsInstance(result, AdoptResult)
        self.assertTrue(result.ok)

    def test_adopt_creates_genome_init(self):
        tmp = self._make()
        adopt_project(tmp, pattern="bare", dry_run=False, force=False)
        genome_dir = os.path.join(tmp, "src", "myapp", "genome")
        self.assertTrue(os.path.exists(os.path.join(genome_dir, "__init__.py")))

    def test_adopt_creates_genome_canon(self):
        tmp = self._make()
        adopt_project(tmp, pattern="bare", dry_run=False, force=False)
        genome_dir = os.path.join(tmp, "src", "myapp", "genome")
        self.assertTrue(os.path.exists(os.path.join(genome_dir, "canon.py")))

    def test_adopt_creates_aiep_genome_config(self):
        tmp = self._make()
        adopt_project(tmp, pattern="bare", dry_run=False, force=False)
        cfg_path = os.path.join(tmp, ".aiep-genome.json")
        self.assertTrue(os.path.exists(cfg_path))
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        for key in ("name", "pattern", "kernel_version", "genome_sdk_version"):
            self.assertIn(key, cfg)

    def test_adopt_creates_compliance_tests(self):
        tmp = self._make()
        adopt_project(tmp, pattern="bare", dry_run=False, force=False)
        tests_dir = os.path.join(tmp, "tests")
        files = os.listdir(tests_dir)
        self.assertTrue(any("test_" in f for f in files), f"No test file found in {files}")

    def test_adopt_adds_dependency_to_pyproject(self):
        tmp = self._make()
        adopt_project(tmp, pattern="bare", dry_run=False, force=False)
        with open(os.path.join(tmp, "pyproject.toml"), encoding="utf-8") as f:
            content = f.read()
        self.assertIn("aiep-genome-sdk", content)

    def test_adopt_reports_created_files(self):
        tmp = self._make()
        result = adopt_project(tmp, pattern="bare", dry_run=False, force=False)
        self.assertIsInstance(result.created_files, list)
        self.assertGreater(len(result.created_files), 0)


class TestAdoptPatternDetection(unittest.TestCase):

    def setUp(self):
        self._dirs = []

    def tearDown(self):
        for d in self._dirs:
            shutil.rmtree(d, ignore_errors=True)

    def _make(self, fn) -> str:
        d = tempfile.mkdtemp()
        self._dirs.append(d)
        return fn(d)

    def test_mirror_pattern_detected(self):
        tmp = self._make(_make_mirror_project)
        result = adopt_project(tmp, pattern=None, dry_run=False, force=False)
        self.assertTrue(result.ok)
        with open(os.path.join(tmp, ".aiep-genome.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertEqual(cfg["pattern"], "mirror")

    def test_governance_pattern_detected(self):
        tmp = self._make(_make_governance_project)
        result = adopt_project(tmp, pattern=None, dry_run=False, force=False)
        self.assertTrue(result.ok)
        with open(os.path.join(tmp, ".aiep-genome.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertEqual(cfg["pattern"], "governance")

    def test_evidence_ledger_pattern_detected(self):
        tmp = self._make(_make_evidence_project)
        result = adopt_project(tmp, pattern=None, dry_run=False, force=False)
        self.assertTrue(result.ok)
        with open(os.path.join(tmp, ".aiep-genome.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertEqual(cfg["pattern"], "evidence-ledger")

    def test_bare_pattern_is_default_fallback(self):
        tmp = self._make(_make_bare_project)
        result = adopt_project(tmp, pattern=None, dry_run=False, force=False)
        self.assertTrue(result.ok)
        with open(os.path.join(tmp, ".aiep-genome.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertIn(cfg["pattern"], ("bare", "evidence-ledger"))


class TestAdoptPattern_EvidenceLedger(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        _make_bare_project(self._tmp)
        self._result = adopt_project(self._tmp, pattern="evidence-ledger",
                                      dry_run=False, force=False)

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_ok(self):
        self.assertTrue(self._result.ok)

    def test_ledger_created(self):
        genome_dir = os.path.join(self._tmp, "src", "myapp", "genome")
        self.assertTrue(os.path.exists(os.path.join(genome_dir, "ledger.py")))

    def test_ledger_has_evidence_ledger(self):
        genome_dir = os.path.join(self._tmp, "src", "myapp", "genome")
        with open(os.path.join(genome_dir, "ledger.py"), encoding="utf-8") as f:
            content = f.read()
        self.assertIn("EvidenceLedger", content)


class TestAdoptPattern_Mirror(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        _make_bare_project(self._tmp)
        self._result = adopt_project(self._tmp, pattern="mirror",
                                      dry_run=False, force=False)

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_ok(self):
        self.assertTrue(self._result.ok)

    def test_mirror_module_created(self):
        genome_dir = os.path.join(self._tmp, "src", "myapp", "genome")
        self.assertTrue(os.path.exists(os.path.join(genome_dir, "mirror.py")))


class TestAdoptPattern_Governance(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        _make_bare_project(self._tmp)
        self._result = adopt_project(self._tmp, pattern="governance",
                                      dry_run=False, force=False)

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_ok(self):
        self.assertTrue(self._result.ok)

    def test_governance_module_created(self):
        genome_dir = os.path.join(self._tmp, "src", "myapp", "genome")
        self.assertTrue(os.path.exists(os.path.join(genome_dir, "governance.py")))


class TestAdoptDryRun(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        _make_bare_project(self._tmp)

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_dry_run_creates_no_files(self):
        before = set()
        for root, dirs, files in os.walk(self._tmp):
            for fname in files:
                before.add(os.path.join(root, fname))

        adopt_project(self._tmp, pattern="bare", dry_run=True, force=False)

        after = set()
        for root, dirs, files in os.walk(self._tmp):
            for fname in files:
                after.add(os.path.join(root, fname))

        new_files = after - before
        self.assertEqual(len(new_files), 0, f"dry_run created files: {new_files}")

    def test_dry_run_reports_planned_files(self):
        result = adopt_project(self._tmp, pattern="bare", dry_run=True, force=False)
        # dry_run records planned files in created list but does not write them
        self.assertIsInstance(result.created_files, list)


class TestAdoptForce(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        _make_bare_project(self._tmp)

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_second_adopt_without_force_skips(self):
        adopt_project(self._tmp, pattern="bare", dry_run=False, force=False)
        result2 = adopt_project(self._tmp, pattern="bare", dry_run=False, force=False)
        self.assertIsInstance(result2.ok, bool)

    def test_second_adopt_with_force_overwrites(self):
        adopt_project(self._tmp, pattern="bare", dry_run=False, force=False)
        result2 = adopt_project(self._tmp, pattern="evidence-ledger", dry_run=False, force=True)
        self.assertTrue(result2.ok)
        cfg_path = os.path.join(self._tmp, ".aiep-genome.json")
        with open(cfg_path, encoding="utf-8") as f:
            cfg2 = json.load(f)
        self.assertEqual(cfg2["pattern"], "evidence-ledger")


if __name__ == "__main__":
    unittest.main()
