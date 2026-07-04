"""In-process coverage for the aces_pack_tools CLI, model, and edge branches.

Complements tests/test_pack_tools.py (which drives the CLI as a subprocess to
prove the ``python -m aces_pack_tools`` contract and real exit codes). These
tests call the CLI in-process so coverage instrumentation sees cli.py, and
exercise the Finding model and a few CLI edge branches directly. All
secret-shaped and denylisted strings are synthetic.
"""

import argparse
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import aces_pack_tools.__main__  # noqa: E402,F401  (covers the module-level imports)
from aces_pack_tools import cli  # noqa: E402
from aces_pack_tools.model import Finding  # noqa: E402
from aces_pack_tools.schema import SchemaIndex  # noqa: E402

INDEX = ROOT / "schemas" / "index.json"
EXAMPLES = ROOT / "schemas" / "examples"
RELEASE = EXAMPLES / "release.v0.example.json"


def _run_main(args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = cli.main(args)
    return code, out.getvalue(), err.getvalue()


class FindingModelTests(unittest.TestCase):
    def test_to_dict_drops_none_fields(self):
        result = Finding("schema", "p.json", "bad", family=None).to_dict()
        self.assertNotIn("family", result)
        self.assertEqual("schema", result["check"])

    def test_to_dict_keeps_family(self):
        self.assertEqual("release", Finding("schema", "p.json", "bad", family="release").to_dict()["family"])

    def test_format_text_with_family(self):
        self.assertIn("[release]", Finding("schema", "p", "m", family="release").format_text())

    def test_format_text_without_path_uses_pack_placeholder(self):
        self.assertIn("<pack>", Finding("packid", "", "m").format_text())


class CliMainTests(unittest.TestCase):
    def test_validate_clean_record_returns_zero(self):
        code, _, _ = _run_main(["validate", str(RELEASE), "--family", "release", "--schema-index", str(INDEX)])
        self.assertEqual(0, code)

    def test_validate_bad_record_text_returns_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "validation.json"
            bad.write_text('{"checks": []}', encoding="utf-8")
            code, out, _ = _run_main(["validate", str(bad), "--family", "validation", "--schema-index", str(INDEX)])
            self.assertEqual(1, code)
            self.assertIn("ERROR", out)

    def test_validate_bad_record_json_returns_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "validation.json"
            bad.write_text('{"checks": []}', encoding="utf-8")
            code, out, _ = _run_main(
                ["validate", str(bad), "--family", "validation", "--schema-index", str(INDEX), "--format", "json"]
            )
            self.assertEqual(1, code)
            self.assertGreater(json.loads(out)["summary"]["errors"], 0)

    def test_validate_directory_returns_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = SchemaIndex(INDEX)
            for family in ("pack-metadata", "compatibility", "provenance", "lifecycle"):
                # Resolve fixtures through the index so a version bump does not strand this.
                obj = (ROOT / index.entry(family).fixtures[0]).read_text(encoding="utf-8")
                (Path(tmp) / f"{family}.json").write_text(obj, encoding="utf-8")
            code, _, _ = _run_main(["validate", tmp, "--schema-index", str(INDEX)])
            self.assertEqual(0, code)

    def test_validate_file_without_family_is_usage_error(self):
        code, _, err = _run_main(["validate", str(RELEASE), "--schema-index", str(INDEX)])
        self.assertEqual(2, code)
        self.assertIn("error", err)

    def test_missing_schema_index_is_usage_error(self):
        code, _, _ = _run_main(
            ["validate", str(RELEASE), "--family", "release", "--schema-index", "/no/such/index.json"]
        )
        self.assertEqual(2, code)

    def test_release_clean_returns_zero(self):
        code, _, _ = _run_main(["release", str(RELEASE), "--schema-index", str(INDEX)])
        self.assertEqual(0, code)

    def test_leak_clean_directory_returns_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "a.md").write_text("a portable ACES scenario pack", encoding="utf-8")
            code, _, _ = _run_main(["leak", tmp])
            self.assertEqual(0, code)

    def test_leak_single_file_with_finding_returns_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            leaky = Path(tmp) / "c.txt"
            leaky.write_text("key = AKIA" + "ABCDEFGHIJKLMNOP", encoding="utf-8")
            code, _, _ = _run_main(["leak", str(leaky)])
            self.assertEqual(1, code)

    def test_leak_missing_file_is_usage_error(self):
        code, _, err = _run_main(["leak", "/no/such/file.txt"])
        self.assertEqual(2, code)
        self.assertIn("error", err)


class CliDenylistTests(unittest.TestCase):
    def test_read_denylist_none_returns_empty(self):
        self.assertEqual((), cli._read_denylist(None))

    def test_read_denylist_skips_comments_and_blanks(self):
        with tempfile.TemporaryDirectory() as tmp:
            denylist = Path(tmp) / "deny.txt"
            denylist.write_text("# comment\n\nacme-internal-catalog\n", encoding="utf-8")
            self.assertEqual(("acme-internal-catalog",), cli._read_denylist(str(denylist)))

    def test_leak_with_denylist_flags_term(self):
        with tempfile.TemporaryDirectory() as tmp:
            denylist = Path(tmp) / "deny.txt"
            denylist.write_text("acme-internal-catalog\n", encoding="utf-8")
            doc = Path(tmp) / "doc.md"
            doc.write_text("see acme-internal-catalog", encoding="utf-8")
            code, _, _ = _run_main(["leak", str(doc), "--denylist", str(denylist)])
            self.assertEqual(1, code)


class CliDispatchTests(unittest.TestCase):
    def test_unknown_command_raises_value_error(self):
        with self.assertRaises(ValueError):
            cli._dispatch(argparse.Namespace(command="bogus"))


if __name__ == "__main__":
    unittest.main()
