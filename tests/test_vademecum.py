import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "skills/pr-review/scripts/vademecum.py"
HEAD = "1" * 40
BASE = "2" * 40
REVIEWERS = (
    "pr-review-slap", "pr-review-kiss", "pr-review-keep-short",
    "pr-review-oop", "pr-review-scope", "pr-review-logic",
    "pr-review-documentation", "pr-review-side-effects",
    "pr-review-complexity",
)

NORMAL_PATCH = """diff --git a/src/a.py b/src/a.py
index 1111111..2222222 100644
--- a/src/a.py
+++ b/src/a.py
@@ -1,2 +1,2 @@
-old
+new
 same
@@ -10 +10,2 @@ def f():
 keep
+added
"""

SPECIAL_PATCH = """diff --git a/old.txt b/new.txt
similarity index 100%
rename from old.txt
rename to new.txt
diff --git a/image.png b/image.png
index 1111111..2222222 100644
Binary files a/image.png and b/image.png differ
diff --git a/tool.sh b/tool.sh
old mode 100644
new mode 100755
"""


class VademecumTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.manifest = self.root / "manifest.md"
        self.patch = self.root / "changes.patch"
        self.directory = self.root / "code-review/vademecum"
        self.manifest.write_text(
            f"# Frozen Review\n\n## Head SHA\n{HEAD}\n\n## Merge Base SHA\n{BASE}\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temporary.cleanup()

    def run_helper(self, *arguments, success=True):
        result = subprocess.run(
            [sys.executable, str(HELPER), *map(str, arguments)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=ROOT,
        )
        if success and result.returncode:
            self.fail(f"command failed: {result.stderr}")
        if not success and not result.returncode:
            self.fail(f"command unexpectedly succeeded: {result.stdout}")
        return result

    def prepare(self, patch=NORMAL_PATCH):
        self.patch.write_text(patch, encoding="utf-8")
        self.run_helper(
            "prepare", "--manifest", self.manifest, "--patch", self.patch,
            "--out-dir", self.directory,
        )
        return re.findall(r"^## Item (I-[0-9a-f]{16})$", (
            self.directory / "_inventory.md").read_text(encoding="utf-8"), re.MULTILINE)

    def draft(self, ids, *, cards=None, head=HEAD, base=BASE):
        if cards is None:
            cards = [
                {
                    "id": "OV-001", "kind": "OV", "title": "PR overview",
                    "facts": ["The PR changes one behavior."],
                    "anchors": [], "links": ["CH-001"], "covers": [],
                },
                {
                    "id": "CH-001", "kind": "CH", "title": "Changed behavior",
                    "facts": ["The patch changes the selected lines."],
                    "anchors": ["src/a.py#L1-L2@new"], "links": ["OV-001"], "covers": ids,
                },
            ]
        lines = [
            "# Vademecum Draft", "", "## Head SHA", head, "",
            "## Merge Base SHA", base, "",
        ]
        for card in cards:
            lines.extend([
                f"## Card {card['id']}", "", "### Kind", card["kind"], "",
                "### Title", card["title"], "", "### Facts",
                *[f"- {fact}" for fact in card["facts"]], "",
                "### Anchors", *([f"- `{x}`" for x in card["anchors"]] or ["None"]), "",
                "### Links", *([f"- `{x}`" for x in card["links"]] or ["None"]), "",
                "### Covers", *([f"- `{x}`" for x in card["covers"]] or ["None"]), "",
            ])
        self.directory.mkdir(parents=True, exist_ok=True)
        (self.directory / "_draft.md").write_text("\n".join(lines), encoding="utf-8")

    def build_basic(self):
        ids = self.prepare()
        self.draft(ids)
        self.run_helper("build", "--dir", self.directory, "--patch", self.patch)
        return ids

    def test_prepare_inventories_multiple_normal_hunks_with_stable_ids(self):
        first = self.prepare()
        self.assertEqual(2, len(first))
        inventory = (self.directory / "_inventory.md").read_text(encoding="utf-8")
        self.assertEqual(2, inventory.count("### Change\nhunk"))
        second = self.prepare()
        self.assertEqual(first, second)

    def test_prepare_inventories_rename_binary_and_mode_only(self):
        ids = self.prepare(SPECIAL_PATCH)
        self.assertEqual(3, len(ids))
        inventory = (self.directory / "_inventory.md").read_text(encoding="utf-8")
        self.assertIn("### Change\nrename", inventory)
        self.assertIn("### Change\nbinary", inventory)
        self.assertIn("### Change\nmode", inventory)

    def test_prepare_decodes_git_quoted_utf8_paths(self):
        patch = (
            'diff --git "a/caf\\303\\251.txt" "b/caf\\303\\251.txt"\n'
            '--- "a/caf\\303\\251.txt"\n'
            '+++ "b/caf\\303\\251.txt"\n'
            '@@ -1 +1 @@\n-old\n+new\n'
        )
        self.prepare(patch)
        inventory = (self.directory / "_inventory.md").read_text(encoding="utf-8")
        self.assertIn("`caf" + chr(0xE9) + ".txt`", inventory)

    def test_prepare_preserves_literal_backslash_in_git_quoted_path(self):
        patch = (
            'diff --git "a/foo\\\\bar.txt" "b/foo\\\\bar.txt"\n'
            '--- "a/foo\\\\bar.txt"\n'
            '+++ "b/foo\\\\bar.txt"\n'
            '@@ -1 +1 @@\n-old\n+new\n'
        )
        self.prepare(patch)
        inventory = (self.directory / "_inventory.md").read_text(encoding="utf-8")
        self.assertIn("`foo\\bar.txt`", inventory)

    def test_prepare_accepts_existing_frontmatter_manifest(self):
        self.manifest.write_text(
            f"---\nhead_sha: {HEAD}\nmerge_base_sha: {BASE}\n---\n# Manifest\n",
            encoding="utf-8",
        )
        self.assertEqual(2, len(self.prepare()))
        self.assertNotIn("---", (self.directory / "_inventory.md").read_text(encoding="utf-8"))

    def test_build_is_deterministic_and_removes_draft(self):
        ids = self.build_basic()
        first = {
            str(path.relative_to(self.directory)): path.read_bytes()
            for path in self.directory.rglob("*.md")
        }
        self.draft(ids)
        self.run_helper("build", "--dir", self.directory, "--patch", self.patch)
        second = {
            str(path.relative_to(self.directory)): path.read_bytes()
            for path in self.directory.rglob("*.md")
        }
        self.assertEqual(first, second)
        self.assertFalse((self.directory / "_draft.md").exists())
        index = (self.directory / "_index.md").read_text(encoding="utf-8")
        self.assertNotIn("I-", index)

    def test_cards_support_bounded_fact_lists_and_require_overview(self):
        ids = self.prepare()
        cards = [
            {"id": "OV-001", "kind": "OV", "title": "Overview",
             "facts": ["Context fact.", "Observable change fact."],
             "anchors": [], "links": ["CH-001"], "covers": []},
            {"id": "CH-001", "kind": "CH", "title": "Change",
             "facts": ["Base fact.", "Head fact."],
             "anchors": ["src/a.py#L1@new"], "links": ["OV-001"], "covers": ids},
        ]
        self.draft(ids, cards=cards)
        self.run_helper("build", "--dir", self.directory, "--patch", self.patch)
        card = (self.directory / "cards/CH-001.md").read_text(encoding="utf-8")
        self.assertIn("## Facts\n- Base fact.\n- Head fact.", card)

        cards[1]["links"] = []
        self.draft(ids, cards=[cards[1]])
        result = self.run_helper(
            "build", "--dir", self.directory, "--patch", self.patch, success=False)
        self.assertIn("requires at least one OV", result.stderr)

    def test_build_replaces_obsolete_cards(self):
        ids = self.build_basic()
        obsolete = self.directory / "cards/CH-999.md"
        obsolete.write_text("obsolete", encoding="utf-8")
        self.draft(ids)
        # Existing generated artifacts may be stale, but their names are known.
        self.run_helper("build", "--dir", self.directory, "--patch", self.patch)
        self.assertFalse(obsolete.exists())

    def test_valid_links_and_repository_relative_anchors(self):
        ids = self.prepare()
        cards = [
            {"id": "OV-001", "kind": "OV", "title": "Overview", "facts": ["One overview fact."],
             "anchors": [], "links": ["CH-001"], "covers": []},
            {"id": "CH-001", "kind": "CH", "title": "Changes", "facts": ["One change fact."],
             "anchors": ["src/a.py#L1@new", "docs/readme.md#L2-L4@old"], "links": ["OV-001"], "covers": ids},
        ]
        self.draft(ids, cards=cards)
        self.run_helper("build", "--dir", self.directory, "--patch", self.patch)
        self.run_helper("check", "--dir", self.directory, "--patch", self.patch)
        self.assertIn("[OV-001](OV-001.md)", (self.directory / "cards/CH-001.md").read_text())

    def test_cover_without_matching_anchor_fails(self):
        ids = self.prepare()
        cards = [
            {"id": "OV-001", "kind": "OV", "title": "Overview", "facts": ["Overview."],
             "anchors": [], "links": ["CH-001"], "covers": []},
            {"id": "CH-001", "kind": "CH", "title": "Changes", "facts": ["One fact."],
             "anchors": ["docs/other.py#L1@new"], "links": ["OV-001"], "covers": ids},
        ]
        self.draft(ids, cards=cards)
        result = self.run_helper(
            "build", "--dir", self.directory, "--patch", self.patch, success=False)
        self.assertIn("requires an anchor on `src/a.py@new`", result.stderr)

    def test_deletion_requires_old_side_anchor(self):
        deletion_patch = (
            "diff --git a/gone.py b/gone.py\n"
            "deleted file mode 100644\n"
            "index 1111111..0000000\n"
            "--- a/gone.py\n"
            "+++ /dev/null\n"
            "@@ -1 +0,0 @@\n"
            "-old\n"
        )
        ids = self.prepare(deletion_patch)
        cards = [
            {"id": "OV-001", "kind": "OV", "title": "Overview", "facts": ["Overview."],
             "anchors": [], "links": ["CH-001"], "covers": []},
            {"id": "CH-001", "kind": "CH", "title": "Deletion", "facts": ["One fact."],
             "anchors": ["gone.py@old"], "links": ["OV-001"], "covers": ids},
        ]
        self.draft(ids, cards=cards)
        self.run_helper("build", "--dir", self.directory, "--patch", self.patch)
        self.run_helper("check", "--dir", self.directory, "--patch", self.patch)

        cards[2 - 1]["anchors"] = ["gone.py#L1@new"]
        self.draft(ids, cards=cards)
        result = self.run_helper(
            "build", "--dir", self.directory, "--patch", self.patch, success=False)
        self.assertIn("requires an anchor on `gone.py@old`", result.stderr)

    def test_rename_requires_new_path_anchor(self):
        rename_patch = (
            "diff --git a/old.txt b/new.txt\n"
            "similarity index 100%\n"
            "rename from old.txt\n"
            "rename to new.txt\n"
        )
        ids = self.prepare(rename_patch)
        cards = [
            {"id": "OV-001", "kind": "OV", "title": "Overview", "facts": ["Overview."],
             "anchors": [], "links": ["CH-001"], "covers": []},
            {"id": "CH-001", "kind": "CH", "title": "Rename", "facts": ["One fact."],
             "anchors": ["new.txt@new"], "links": ["OV-001"], "covers": ids},
        ]
        self.draft(ids, cards=cards)
        self.run_helper("build", "--dir", self.directory, "--patch", self.patch)
        self.run_helper("check", "--dir", self.directory, "--patch", self.patch)

        cards[1]["anchors"] = ["old.txt@old"]
        self.draft(ids, cards=cards)
        result = self.run_helper(
            "build", "--dir", self.directory, "--patch", self.patch, success=False)
        self.assertIn("requires an anchor on `new.txt@new`", result.stderr)

    def test_multi_hunk_same_file_card_passes(self):
        ids = self.prepare()
        cards = [
            {"id": "OV-001", "kind": "OV", "title": "Overview", "facts": ["Overview."],
             "anchors": [], "links": ["CH-001"], "covers": []},
            {"id": "CH-001", "kind": "CH", "title": "Changes", "facts": ["One fact."],
             "anchors": ["src/a.py@new"], "links": ["OV-001"], "covers": ids},
        ]
        self.draft(ids, cards=cards)
        self.run_helper("build", "--dir", self.directory, "--patch", self.patch)
        self.run_helper("check", "--dir", self.directory, "--patch", self.patch)

    def test_path_only_anchor_accepted_for_binary_and_mode(self):
        ids = self.prepare(SPECIAL_PATCH)
        inventory = (self.directory / "_inventory.md").read_text(encoding="utf-8")
        item_by_path = {
            path: item for item, path in re.findall(
                r"^## Item (I-[0-9a-f]{16})\n\n### Path\n`([^`]+)`", inventory, re.MULTILINE)}
        cards = [
            {"id": "OV-001", "kind": "OV", "title": "Overview", "facts": ["Overview."],
             "anchors": [], "links": [], "covers": []},
            {"id": "CH-001", "kind": "CH", "title": "Rename", "facts": ["One fact."],
             "anchors": ["new.txt@new"], "links": [], "covers": [item_by_path["new.txt"]]},
            {"id": "CH-002", "kind": "CH", "title": "Binary", "facts": ["One fact."],
             "anchors": ["image.png@new"], "links": [], "covers": [item_by_path["image.png"]]},
            {"id": "CH-003", "kind": "CH", "title": "Mode", "facts": ["One fact."],
             "anchors": ["tool.sh@new"], "links": [], "covers": [item_by_path["tool.sh"]]},
        ]
        self.draft(ids, cards=cards)
        self.run_helper("build", "--dir", self.directory, "--patch", self.patch)
        self.run_helper("check", "--dir", self.directory, "--patch", self.patch)

    def test_inventory_records_structured_old_and_new_paths(self):
        self.prepare(SPECIAL_PATCH)
        inventory = (self.directory / "_inventory.md").read_text(encoding="utf-8")
        self.assertIn("### Old Path\n`old.txt`", inventory)
        self.assertIn("### New Path\n`new.txt`", inventory)
        self.assertIn("### Old Path\n`image.png`", inventory)
        self.assertIn("### New Path\n`image.png`", inventory)
        self.assertNotIn("### Old Path\nNone", inventory)
        self.assertNotIn("### New Path\nNone", inventory)

    def test_inventory_records_deletion_paths(self):
        deletion_patch = (
            "diff --git a/gone.py b/gone.py\n"
            "deleted file mode 100644\n"
            "index 1111111..0000000\n"
            "--- a/gone.py\n"
            "+++ /dev/null\n"
            "@@ -1 +0,0 @@\n"
            "-old\n"
        )
        self.prepare(deletion_patch)
        inventory = (self.directory / "_inventory.md").read_text(encoding="utf-8")
        self.assertIn("### Old Path\n`gone.py`", inventory)
        self.assertIn("### New Path\nNone", inventory)

    def assert_bad_draft(self, mutate, expected=None):
        ids = self.prepare()
        self.draft(ids)
        draft_path = self.directory / "_draft.md"
        original = draft_path.read_text(encoding="utf-8")
        draft_path.write_text(mutate(original, ids), encoding="utf-8")
        sentinel = "prior index\n"
        (self.directory / "_index.md").write_text(sentinel, encoding="utf-8")
        result = self.run_helper(
            "build", "--dir", self.directory, "--patch", self.patch, success=False)
        if expected:
            self.assertIn(expected, result.stderr)
        self.assertEqual(sentinel, (self.directory / "_index.md").read_text(encoding="utf-8"))
        self.assertFalse((self.directory / "cards").exists())
        self.assertTrue(draft_path.exists())

    def test_build_failure_is_atomic(self):
        self.assert_bad_draft(lambda text, _ids: text.replace("CH-001\n", "CH-001\n", 1).replace(
            "- `I-", "- `I-deadbeefdeadbeef`\n- `I-", 1), "unknown inventory")

    def test_build_rejects_inventory_edited_before_sealing(self):
        ids = self.prepare()
        inventory_path = self.directory / "_inventory.md"
        inventory = inventory_path.read_text(encoding="utf-8")
        start = inventory.index(f"## Item {ids[1]}")
        inventory_path.write_text(inventory[:start], encoding="utf-8")
        self.draft([ids[0]])
        result = self.run_helper(
            "build", "--dir", self.directory, "--patch", self.patch,
            success=False)
        self.assertIn("does not match the frozen patch inventory", result.stderr)

    def test_check_rejects_changed_frozen_patch(self):
        self.build_basic()
        self.patch.write_text(NORMAL_PATCH + "\n", encoding="utf-8")
        result = self.run_helper(
            "check", "--dir", self.directory, "--patch", self.patch,
            success=False)
        self.assertIn("patch hash does not match", result.stderr)

    def test_rejects_wrong_identity(self):
        self.assert_bad_draft(lambda text, _ids: text.replace(HEAD, "3" * 40), "identity")

    def test_rejects_duplicate_cards(self):
        def duplicate(text, _ids):
            block = text[text.index("## Card CH-001"):]
            return text + block
        self.assert_bad_draft(duplicate, "duplicate card ID")

    def test_rejects_bad_kinds_and_kind_id_mismatch(self):
        for replacement in ("XX", "OV"):
            with self.subTest(kind=replacement):
                self.assert_bad_draft(lambda text, _ids, value=replacement: text.replace(
                    "### Kind\nCH", f"### Kind\n{value}"))

    def test_rejects_title_and_fact_limits(self):
        self.assert_bad_draft(lambda text, _ids: text.replace("Changed behavior", "x" * 81), "title exceeds")
        self.assert_bad_draft(lambda text, _ids: text.replace(
            "The patch changes the selected lines.", "x" * 241), "exceeds")

    def test_rejects_bad_paths_and_links(self):
        replacements = [
            ("src/a.py#L1-L2@new", "../secret#L1@new", "traverse"),
            ("- `OV-001`\n\n### Covers", "- `OV-999`\n\n### Covers", "missing card"),
        ]
        for old, new, error in replacements:
            with self.subTest(new=new):
                self.assert_bad_draft(lambda text, _ids, a=old, b=new: text.replace(a, b), error)

    def test_rejects_missing_and_non_ch_coverage(self):
        self.assert_bad_draft(lambda text, _ids: re.sub(
            r"### Covers\n(?:- `[^`]+`\n)+", "### Covers\nNone\n", text), "not covered")
        self.assert_bad_draft(lambda text, _ids: text.replace("CH-001", "FL-001").replace(
            "### Kind\nCH", "### Kind\nFL"), "only CH")

    def test_rejects_malformed_markdown_heading_order(self):
        self.assert_bad_draft(lambda text, _ids: text.replace("### Facts", "#### Facts"), "headings must")
        self.assert_bad_draft(lambda text, _ids: text.replace("# Vademecum Draft", "///\n# Vademecum Draft"),
                              "invalid title")

    def test_check_detects_card_index_and_seal_tampering(self):
        targets = ["cards/CH-001.md", "_index.md", "_seal.md"]
        for target in targets:
            with self.subTest(target=target):
                self.build_basic()
                path = self.directory / target
                path.write_text(path.read_text(encoding="utf-8") + "tampered\n", encoding="utf-8")
                self.run_helper(
                    "check", "--dir", self.directory, "--patch", self.patch,
                    success=False)
                # Reset the whole fixture for the next subtest.
                for child in sorted(self.directory.rglob("*"), reverse=True):
                    if child.is_file():
                        child.unlink()
                    elif child.is_dir():
                        child.rmdir()

    def test_check_rejects_unexpected_markdown_and_non_markdown_files(self):
        for name in ("extra.md", "data.json"):
            with self.subTest(name=name):
                self.build_basic()
                (self.directory / name).write_text("unexpected", encoding="utf-8")
                result = self.run_helper(
                    "check", "--dir", self.directory, "--patch", self.patch,
                    success=False)
                self.assertIn("unexpected" if name.endswith(".md") else "non-Markdown", result.stderr)
                (self.directory / name).unlink()

    def test_seal_contains_hashes_for_complete_artifact_set(self):
        self.build_basic()
        seal = (self.directory / "_seal.md").read_text(encoding="utf-8")
        hashed = dict((path, digest) for digest, path in re.findall(
            r"^### SHA-256 ([0-9a-f]{64}) (.+)$", seal, re.MULTILINE))
        expected = {"_inventory.md", "_index.md", "cards/CH-001.md", "cards/OV-001.md"}
        self.assertEqual(expected, set(hashed))
        for relative, digest in hashed.items():
            self.assertEqual(hashlib.sha256((self.directory / relative).read_bytes()).hexdigest(), digest)

    def test_all_reviewers_use_the_shared_context_contract(self):
        for reviewer in REVIEWERS:
            with self.subTest(reviewer=reviewer):
                text = (ROOT / f"skills/{reviewer}/SKILL.md").read_text(encoding="utf-8")
                normalized = " ".join(text.split())
                self.assertIn("vademecum/_index.md` first", normalized)
                self.assertIn("Do not begin with a broad patch", normalized)
                self.assertIn("bounded frozen target", normalized)
                self.assertIn("relevant card IDs", normalized)
                self.assertIn("pr-review-validator", normalized)
                self.assertIn("user chose legacy fallback", normalized)

    def test_prepare_build_check_survive_triple_dash_in_path_and_fact(self):
        patch = (
            "diff --git a/docs/a---b.md b/docs/a---b.md\n"
            "new file mode 100644\n"
            "index 1111111..2222222\n"
            "--- /dev/null\n"
            "+++ b/docs/a---b.md\n"
            "@@ -0,0 +1 @@\n"
            "+x = y---z\n"
        )
        ids = self.prepare(patch)
        self.assertEqual(1, len(ids))
        inventory = (self.directory / "_inventory.md").read_text(encoding="utf-8")
        self.assertIn("`docs/a---b.md`", inventory)
        self.assertIn("@@ -0,0 +1 @@", inventory)
        cards = [
            {"id": "OV-001", "kind": "OV", "title": "Overview", "facts": ["Overview."],
             "anchors": [], "links": ["CH-001"], "covers": []},
            {"id": "CH-001", "kind": "CH", "title": "Dashes", "facts": ["fact with --- inside."],
             "anchors": ["docs/a---b.md#L1@new"], "links": ["OV-001"], "covers": ids},
        ]
        self.draft(ids, cards=cards)
        self.run_helper("build", "--dir", self.directory, "--patch", self.patch)
        self.run_helper("check", "--dir", self.directory, "--patch", self.patch)

    def test_frontmatter_still_rejected_at_document_start(self):
        self.prepare()
        ids = self.prepare()
        self.draft(ids)
        draft_path = self.directory / "_draft.md"
        draft_path.write_text("---\nforwarded: true\n---\n" + draft_path.read_text(encoding="utf-8"),
                              encoding="utf-8")
        result = self.run_helper(
            "build", "--dir", self.directory, "--patch", self.patch, success=False)
        self.assertIn("frontmatter is forbidden", result.stderr)

    def test_check_with_recorded_seal_hash_detects_consistent_tampering(self):
        self.build_basic()
        hash_file = Path(str(self.directory) + ".seal-hash")
        recorded = hash_file.read_text(encoding="utf-8").strip()
        self.assertEqual(
            hashlib.sha256((self.directory / "_seal.md").read_bytes()).hexdigest(), recorded)
        # A second, self-consistent build (different fact) represents an
        # attacker who regenerated cards, index, and seal with the helper.
        ids = re.findall(r"^## Item (I-[0-9a-f]{16})$", (
            self.directory / "_inventory.md").read_text(encoding="utf-8"), re.MULTILINE)
        original_fact = "The patch changes the selected lines."
        cards = [
            {"id": "OV-001", "kind": "OV", "title": "Overview", "facts": ["Overview."],
             "anchors": [], "links": ["CH-001"], "covers": []},
            {"id": "CH-001", "kind": "CH", "title": "Changed behavior",
             "facts": ["TAMPERED fact."],
             "anchors": ["src/a.py#L1-L2@new"], "links": ["OV-001"], "covers": ids},
        ]
        self.draft(ids, cards=cards)
        self.run_helper("build", "--dir", self.directory, "--patch", self.patch)
        card = (self.directory / "cards/CH-001.md").read_text(encoding="utf-8")
        self.assertIn("TAMPERED", card)
        self.assertNotIn(original_fact, card)
        # The stale recorded hash anchors the seal outside the writable tree.
        hash_file.write_text(recorded, encoding="utf-8")
        result = self.run_helper(
            "check", "--dir", self.directory, "--patch", self.patch, success=False)
        self.assertIn("seal hash mismatch", result.stderr)
        # Without the recorded hash, plain check still validates structure.
        hash_file.unlink()
        self.run_helper("check", "--dir", self.directory, "--patch", self.patch)

    def test_interrupted_swap_self_heals_on_next_invocation(self):
        ids = self.build_basic()
        backup = Path(str(self.directory) + ".vademecum-backup")
        # Simulate a crash between the two renames: target gone, backup present.
        os.replace(self.directory, backup)
        # Next invocation restores the sealed directory before proceeding.
        self.run_helper("check", "--dir", self.directory, "--patch", self.patch)
        self.assertTrue(self.directory.is_dir())
        self.assertFalse(backup.exists())
        # Re-author the draft (build consumed it) and rebuild end to end.
        self.draft(ids)
        self.run_helper("build", "--dir", self.directory, "--patch", self.patch)
        self.run_helper("check", "--dir", self.directory, "--patch", self.patch)


if __name__ == "__main__":
    unittest.main()
