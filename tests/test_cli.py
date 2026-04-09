"""Tests for aiep-genome CLI — subprocess integration tests."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest


def _run(*args, cwd=None):
    """Run aiep_genome CLI as a subprocess, return (stdout, stderr, returncode)."""
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "aiep_genome", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        cwd=cwd,
    )
    return result.stdout, result.stderr, result.returncode


def _make_bare_project(tmp: str, name: str = "myapp") -> str:
    src_dir = os.path.join(tmp, "src", name)
    os.makedirs(src_dir, exist_ok=True)
    with open(os.path.join(src_dir, "__init__.py"), "w", encoding="utf-8") as f:
        f.write('__version__ = "0.1.0"\n')
    with open(os.path.join(tmp, "pyproject.toml"), "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(f"""\
            [build-system]
            requires = ["setuptools"]
            build-backend = "setuptools.backends.legacy:build"

            [project]
            name = "{name}"
            version = "0.1.0"
            dependencies = []
        """))
    os.makedirs(os.path.join(tmp, "tests"), exist_ok=True)
    return tmp


class TestCLISelfTest(unittest.TestCase):

    def test_self_test_passes(self):
        stdout, stderr, rc = _run("--self-test")
        self.assertEqual(rc, 0, f"--self-test failed: {stderr}")
        self.assertIn("PASS", stdout.upper())

    def test_self_test_no_error_output(self):
        stdout, stderr, rc = _run("--self-test")
        self.assertEqual(rc, 0)
        # No tracebacks
        self.assertNotIn("Traceback", stderr)


class TestCLIHelp(unittest.TestCase):

    def test_help_exit_code(self):
        _, _, rc = _run("--help")
        self.assertEqual(rc, 0)

    def test_help_lists_subcommands(self):
        stdout, _, _ = _run("--help")
        for cmd in ("init", "adopt", "verify", "status"):
            self.assertIn(cmd, stdout)

    def test_init_help(self):
        stdout, _, rc = _run("init", "--help")
        self.assertEqual(rc, 0)
        self.assertIn("--name", stdout)
        self.assertIn("--pattern", stdout)

    def test_adopt_help(self):
        stdout, _, rc = _run("adopt", "--help")
        self.assertEqual(rc, 0)
        self.assertIn("--dry-run", stdout)

    def test_verify_help(self):
        stdout, _, rc = _run("verify", "--help")
        self.assertEqual(rc, 0)


class TestCLIInit(unittest.TestCase):

    def setUp(self):
        self._dirs = []

    def tearDown(self):
        for d in self._dirs:
            shutil.rmtree(d, ignore_errors=True)

    def _tmp(self):
        d = tempfile.mkdtemp()
        self._dirs.append(d)
        return d

    def test_init_creates_directory(self):
        tmp = self._tmp()
        dest = os.path.join(tmp, "new_proj")
        stdout, stderr, rc = _run("init", dest, "--name", "new_proj")
        self.assertEqual(rc, 0, f"Non-zero exit: {stderr}")

    def test_init_creates_pyproject_toml(self):
        tmp = self._tmp()
        dest = os.path.join(tmp, "new_proj")
        _run("init", dest, "--name", "new_proj")
        self.assertTrue(os.path.exists(os.path.join(dest, "pyproject.toml")))

    def test_init_creates_aiep_genome_config(self):
        tmp = self._tmp()
        dest = os.path.join(tmp, "new_proj")
        _run("init", dest, "--name", "new_proj")
        cfg_path = os.path.join(dest, ".aiep-genome.json")
        self.assertTrue(os.path.exists(cfg_path))
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertEqual(cfg["name"], "new_proj")

    def test_init_bare_pattern(self):
        tmp = self._tmp()
        dest = os.path.join(tmp, "bare_proj")
        stdout, _, rc = _run("init", dest, "--name", "bare_proj", "--pattern", "bare")
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists(os.path.join(dest, "src", "bare_proj", "genome", "__init__.py")))

    def test_init_evidence_ledger_pattern(self):
        tmp = self._tmp()
        dest = os.path.join(tmp, "el_proj")
        _run("init", dest, "--name", "el_proj", "--pattern", "evidence-ledger")
        self.assertTrue(os.path.exists(os.path.join(dest, "src", "el_proj", "genome", "ledger.py")))

    def test_init_mirror_pattern(self):
        tmp = self._tmp()
        dest = os.path.join(tmp, "m_proj")
        _run("init", dest, "--name", "m_proj", "--pattern", "mirror")
        self.assertTrue(os.path.exists(os.path.join(dest, "src", "m_proj", "genome", "mirror.py")))

    def test_init_governance_pattern(self):
        tmp = self._tmp()
        dest = os.path.join(tmp, "g_proj")
        _run("init", dest, "--name", "g_proj", "--pattern", "governance")
        self.assertTrue(os.path.exists(os.path.join(dest, "src", "g_proj", "genome", "governance.py")))

    def test_init_output_mentions_pattern(self):
        tmp = self._tmp()
        dest = os.path.join(tmp, "out_proj")
        stdout, _, _ = _run("init", dest, "--name", "out_proj", "--pattern", "bare")
        self.assertIn("bare", stdout.lower())

    def test_init_force_flag(self):
        tmp = self._tmp()
        dest = os.path.join(tmp, "f_proj")
        _run("init", dest, "--name", "f_proj", "--pattern", "bare")
        stdout, stderr, rc = _run("init", dest, "--name", "f_proj",
                                   "--pattern", "bare", "--force")
        self.assertEqual(rc, 0, f"Force re-init failed: {stderr}")


class TestCLIAdopt(unittest.TestCase):

    def setUp(self):
        self._dirs = []

    def tearDown(self):
        for d in self._dirs:
            shutil.rmtree(d, ignore_errors=True)

    def _make(self) -> str:
        d = tempfile.mkdtemp()
        self._dirs.append(d)
        return _make_bare_project(d)

    def test_adopt_succeeds(self):
        tmp = self._make()
        stdout, stderr, rc = _run("adopt", tmp)
        self.assertEqual(rc, 0, f"adopt failed: {stderr}")

    def test_adopt_creates_genome_dir(self):
        tmp = self._make()
        _run("adopt", tmp)
        # Genome dir is placed inside the detected package src dir
        src_genome = os.path.join(tmp, "src", "myapp", "genome")
        root_genome = os.path.join(tmp, "genome")
        self.assertTrue(
            os.path.exists(src_genome) or os.path.exists(root_genome),
            f"No genome dir found at {src_genome} or {root_genome}",
        )

    def test_adopt_creates_config(self):
        tmp = self._make()
        _run("adopt", tmp)
        self.assertTrue(os.path.exists(os.path.join(tmp, ".aiep-genome.json")))

    def test_adopt_dry_run_creates_nothing(self):
        tmp = self._make()
        before = set()
        for root, _, files in os.walk(tmp):
            for fname in files:
                before.add(os.path.join(root, fname))

        _run("adopt", tmp, "--dry-run")

        after = set()
        for root, _, files in os.walk(tmp):
            for fname in files:
                after.add(os.path.join(root, fname))

        new_files = after - before
        self.assertEqual(len(new_files), 0, f"dry-run created files: {new_files}")

    def test_adopt_dry_run_output(self):
        tmp = self._make()
        stdout, _, rc = _run("adopt", tmp, "--dry-run")
        self.assertEqual(rc, 0)
        # Should mention DRY RUN or preview
        self.assertRegex(stdout.upper(), r"DRY.?RUN|PREVIEW|PLANNED|WOULD")

    def test_adopt_with_explicit_pattern(self):
        tmp = self._make()
        stdout, stderr, rc = _run("adopt", tmp, "--pattern", "evidence-ledger")
        self.assertEqual(rc, 0, f"explicit pattern failed: {stderr}")
        src_ledger = os.path.join(tmp, "src", "myapp", "genome", "ledger.py")
        root_ledger = os.path.join(tmp, "genome", "ledger.py")
        self.assertTrue(
            os.path.exists(src_ledger) or os.path.exists(root_ledger),
            f"no ledger.py found",
        )

    def test_adopt_reports_files_created(self):
        tmp = self._make()
        stdout, _, rc = _run("adopt", tmp)
        self.assertEqual(rc, 0)
        self.assertRegex(stdout, r"genome|created|adopted", re.IGNORECASE)


class TestCLIVerify(unittest.TestCase):

    def setUp(self):
        self._dirs = []

    def tearDown(self):
        for d in self._dirs:
            shutil.rmtree(d, ignore_errors=True)

    def test_verify_on_adopted_project(self):
        d = tempfile.mkdtemp()
        self._dirs.append(d)
        _make_bare_project(d)
        _run("adopt", d)
        stdout, stderr, rc = _run("verify", d)
        # Should complete without internal error
        self.assertNotIn("Traceback", stderr)
        self.assertIn("C", stdout)  # At least one check label present

    def test_verify_on_empty_dir_nonzero_or_report(self):
        d = tempfile.mkdtemp()
        self._dirs.append(d)
        stdout, stderr, rc = _run("verify", d)
        # Either non-zero exit or output showing failures
        if rc == 0:
            self.assertRegex(stdout.upper(), r"FAIL|MISSING|ERROR|WARN")

    def test_verify_on_init_project(self):
        d = tempfile.mkdtemp()
        self._dirs.append(d)
        dest = os.path.join(d, "vproj")
        _run("init", dest, "--name", "vproj", "--pattern", "bare")
        stdout, stderr, rc = _run("verify", dest)
        self.assertNotIn("Traceback", stderr)


class TestCLIStatus(unittest.TestCase):

    def setUp(self):
        self._dirs = []

    def tearDown(self):
        for d in self._dirs:
            shutil.rmtree(d, ignore_errors=True)

    def test_status_in_adopted_project(self):
        d = tempfile.mkdtemp()
        self._dirs.append(d)
        _make_bare_project(d)
        _run("adopt", d)
        stdout, stderr, rc = _run("status", cwd=d)
        self.assertNotIn("Traceback", stderr)
        self.assertIn("genome", stdout.lower())

    def test_status_in_initd_project(self):
        d = tempfile.mkdtemp()
        self._dirs.append(d)
        dest = os.path.join(d, "sp")
        _run("init", dest, "--name", "sp", "--pattern", "bare")
        stdout, stderr, rc = _run("status", cwd=dest)
        self.assertNotIn("Traceback", stderr)

    def test_status_no_config_nonzero_or_message(self):
        d = tempfile.mkdtemp()
        self._dirs.append(d)
        stdout, stderr, rc = _run("status", cwd=d)
        if rc == 0:
            self.assertRegex(stdout.upper(), r"NOT FOUND|NO CONFIG|MISSING")



if __name__ == "__main__":
    unittest.main()
