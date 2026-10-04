"""Verify the submission archive contains only reviewable project sources."""

import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from make_archive import build_archive


class ArchiveTests(unittest.TestCase):
    def test_archive_uses_source_allowlist_and_contains_no_readme(self):
        with tempfile.TemporaryDirectory() as directory:
            archive_path = build_archive(Path(directory) / "project.zip")
            with ZipFile(archive_path) as archive:
                names = archive.namelist()
                self.assertIsNone(archive.testzip())
        self.assertIn("recommendation_system/engine.py", names)
        self.assertIn("recommendation_system/data/activities.json", names)
        self.assertIn("recommendation_system/web/app.js", names)
        for name in names:
            self.assertNotIn(".venv", name)
            self.assertNotIn("__pycache__", name)
            self.assertFalse(Path(name).name.lower().startswith("readme"))
            self.assertTrue(name.startswith("recommendation_system/"))
        self.assertEqual(len(names), 12)


if __name__ == "__main__":
    unittest.main()
