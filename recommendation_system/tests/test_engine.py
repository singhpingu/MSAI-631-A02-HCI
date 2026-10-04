"""Behavioral checks for ranking, constraints, explanations and malformed input."""

import json
import tempfile
import unittest
from pathlib import Path

from engine import Recommender

ROOT = Path(__file__).resolve().parents[1]


class RecommendationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = Recommender(ROOT / "data" / "activities.json")

    def test_catalogue_has_original_activities_with_unique_ids(self):
        self.assertEqual(len(self.engine.activities), 24)
        self.assertEqual(len(self.engine.id_to_index), 24)
        self.assertTrue(all(item.steps for item in self.engine.activities))

    def test_python_dictionary_interest_ranks_dictionary_activity_first(self):
        result = self.engine.recommend({"query": "Python dictionaries lookup", "diversity": 0})
        self.assertEqual(result["mode"], "personalized")
        self.assertEqual(result["results"][0]["id"], "P01")

    def test_usable_results_obey_all_hard_filters(self):
        result = self.engine.recommend({"topics": ["Usability"], "max_minutes": 20,
                                        "level": "Beginner", "format": "Practice"})
        self.assertTrue(result["results"])
        for item in result["results"]:
            self.assertLessEqual(item["duration_minutes"], 20)
            self.assertEqual(item["level"], "Beginner")
            self.assertEqual(item["format"], "Practice")

    def test_liked_and_hidden_items_are_excluded(self):
        result = self.engine.recommend({"query": "usability", "liked_ids": ["U01"],
                                        "hidden_ids": ["U02"], "max_minutes": 60})
        ids = {item["id"] for item in result["results"]}
        self.assertNotIn("U01", ids)
        self.assertNotIn("U02", ids)

    def test_liked_activity_creates_profile_without_typed_query(self):
        result = self.engine.recommend({"liked_ids": ["P01"], "max_minutes": 60})
        self.assertEqual(result["mode"], "personalized")
        self.assertTrue(result["results"])
        self.assertNotIn("P01", {item["id"] for item in result["results"]})

    def test_unknown_terms_produce_labeled_starter_results(self):
        result = self.engine.recommend({"query": "zzqxvplm"})
        self.assertEqual(result["mode"], "starter")
        self.assertIn("Starter", result["notice"])
        self.assertTrue(all(item["similarity"] is None for item in result["results"]))

    def test_empty_filters_have_actionable_recovery(self):
        result = self.engine.recommend({"max_minutes": 5})
        self.assertEqual(result["results"], [])
        self.assertIn("Increase available time", result["notice"])

    def test_known_profile_does_not_pad_with_unrelated_items(self):
        result = self.engine.recommend({"query": "dictionaries", "count": 8})
        self.assertTrue(result["results"])
        self.assertTrue(all(item["similarity"] > 0 for item in result["results"]))
        self.assertLess(len(result["results"]), 8)

    def test_explanation_terms_are_shared_features(self):
        result = self.engine.recommend({"query": "Python dictionaries lookup"})
        for item in result["results"]:
            terms = self.engine.vectorizer.build_analyzer()(self.engine.activities[
                self.engine.id_to_index[item["id"]]].document)
            self.assertTrue(item["matched_terms"])
            self.assertTrue(set(item["matched_terms"]).issubset(set(terms)))

    def test_scores_are_finite_and_bounded(self):
        result = self.engine.recommend({"topics": list(self.engine.topics), "max_minutes": 60})
        for item in result["results"]:
            self.assertGreaterEqual(item["similarity"], 0)
            self.assertLessEqual(item["similarity"], 1)

    def test_ranking_is_deterministic_and_unique(self):
        payload = {"topics": ["Usability", "AI Ethics"], "max_minutes": 60, "count": 8}
        first = self.engine.recommend(payload)
        self.assertEqual(first, self.engine.recommend(payload))
        ids = [item["id"] for item in first["results"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_variety_can_reduce_duplicate_content(self):
        # Controlled corpus: a lower similarity independent item should replace
        # a near duplicate in the second position when variety is requested.
        base = dict(topic="Test", level="Beginner", duration_minutes=10, format="Practice",
                    tags=[], steps=["Inspect the example."])
        rows = [{**base, "id": "1", "title": "alpha beta gamma", "description": "alpha beta gamma"},
                {**base, "id": "2", "title": "alpha beta gamma", "description": "alpha beta gamma"},
                {**base, "id": "3", "title": "alpha delta epsilon", "description": "alpha delta epsilon"}]
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "items.json"
            file.write_text(json.dumps(rows), encoding="utf-8")
            engine = Recommender(file)
            focused = engine.recommend({"query": "alpha beta gamma delta", "count": 2, "diversity": 0})
            varied = engine.recommend({"query": "alpha beta gamma delta", "count": 2, "diversity": 0.7})
        self.assertEqual([item["id"] for item in focused["results"]], ["1", "2"])
        self.assertEqual([item["id"] for item in varied["results"]], ["1", "3"])

    def test_bad_input_types_and_bounds_are_rejected(self):
        malformed = [[], {"query": 1}, {"query": "a" * 801}, {"topics": ["Unknown"]},
                     {"liked_ids": ["unknown"]}, {"hidden_ids": "U01"}, {"level": []},
                     {"format": "Video"}, {"max_minutes": True}, {"max_minutes": 121},
                     {"count": 0}, {"count": "5"}, {"diversity": float("nan")},
                     {"diversity": True}, {"diversity": -0.1}]
        for payload in malformed:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.engine.recommend(payload)

    def test_duplicate_preferences_are_normalized(self):
        prefs = self.engine.parse_preferences({"topics": ["Python", "Python"],
                                               "liked_ids": ["P01", "P01"]})
        self.assertEqual(prefs.topics, ("Python",))
        self.assertEqual(prefs.liked_ids, ("P01",))

    def test_duplicate_catalogue_ids_are_rejected(self):
        rows = json.loads((ROOT / "data" / "activities.json").read_text())
        rows[1]["id"] = rows[0]["id"]
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "bad.json"
            file.write_text(json.dumps(rows))
            with self.assertRaises(ValueError):
                Recommender(file)


if __name__ == "__main__":
    unittest.main()
