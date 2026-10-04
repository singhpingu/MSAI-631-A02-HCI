"""StudyPath content based recommendations.

Conceptual foundation: Recommenders contributors (n.d.), tfidf_covid.ipynb,
https://github.com/recommenders-team/recommenders/blob/main/examples/00_quick_start/tfidf_covid.ipynb
That MIT licensed example recommends related research articles with TF IDF.
This independently written implementation changes the domain, profile, filters,
ranking and explanations. No upstream notebook code or dataset is bundled.
AI assistance: ChatGPT/Codex helped prepare this implementation and its tests.
The student must review, modify and verify it locally before submission.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize

LEVELS = frozenset({"Beginner", "Intermediate", "Advanced"})
FORMATS = frozenset({"Practice", "Reading", "Reflection"})


@dataclass(frozen=True, slots=True)
class Activity:
    """Immutable catalogue record; IDs remain stable when titles change."""

    id: str
    title: str
    description: str
    topic: str
    level: str
    duration_minutes: int
    format: str
    tags: tuple[str, ...]
    steps: tuple[str, ...]

    @property
    def document(self) -> str:
        return " ".join((self.title, self.description, self.topic, *self.tags))


@dataclass(frozen=True, slots=True)
class Preferences:
    query: str = ""
    topics: tuple[str, ...] = ()
    max_minutes: int = 30
    level: str = "Any"
    format: str = "Any"
    liked_ids: tuple[str, ...] = ()
    hidden_ids: tuple[str, ...] = ()
    count: int = 5
    diversity: float = 0.25


class Recommender:
    """Fit one sparse index at startup and reuse it for every request."""

    def __init__(self, catalogue_path: Path):
        records = json.loads(catalogue_path.read_text(encoding="utf-8"))
        if not isinstance(records, list) or not records:
            raise ValueError("The catalogue must contain activities.")
        activities: list[Activity] = []
        for record in records:
            item = Activity(**{**record, "tags": tuple(record["tags"]),
                               "steps": tuple(record["steps"])})
            if item.level not in LEVELS or item.format not in FORMATS:
                raise ValueError("Unsupported catalogue level or format.")
            if type(item.duration_minutes) is not int or item.duration_minutes < 1:
                raise ValueError("Activity durations must be positive integers.")
            if not all((item.id, item.title, item.description, item.topic, item.steps)):
                raise ValueError("Catalogue fields cannot be empty.")
            activities.append(item)
        self.activities = tuple(activities)
        self.id_to_index = {item.id: i for i, item in enumerate(self.activities)}
        if len(self.id_to_index) != len(self.activities):
            raise ValueError("Activity IDs must be unique.")
        self.topics = tuple(sorted({item.topic for item in self.activities}))
        # Sparse vectors retain only nonzero features; no full dense item matrix.
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2),
                                          sublinear_tf=True, norm="l2")
        self.matrix = self.vectorizer.fit_transform(
            [item.document for item in self.activities]
        ).tocsr()
        self.feature_names = self.vectorizer.get_feature_names_out()

    def parse_preferences(self, payload: Any) -> Preferences:
        """Validate untrusted browser input before it reaches the ranker."""
        if not isinstance(payload, dict):
            raise ValueError("Preferences must be a JSON object.")
        query = payload.get("query", "")
        if not isinstance(query, str) or len(query) > 800:
            raise ValueError("Enter an interest of 800 characters or fewer.")

        def choices(name: str, allowed: set[str] | frozenset[str]) -> tuple[str, ...]:
            values = payload.get(name, [])
            if not isinstance(values, list) or len(values) > 50:
                raise ValueError(f"{name} must be a short list.")
            if any(not isinstance(v, str) or v not in allowed for v in values):
                raise ValueError(f"Unknown value in {name}.")
            # Preserve user order while removing duplicate IDs or topics.
            return tuple(dict.fromkeys(values))

        topics = choices("topics", set(self.topics))
        liked = choices("liked_ids", set(self.id_to_index))
        hidden = choices("hidden_ids", set(self.id_to_index))
        level, item_format = payload.get("level", "Any"), payload.get("format", "Any")
        if not isinstance(level, str) or level not in LEVELS | {"Any"}:
            raise ValueError("Choose a supported difficulty.")
        if not isinstance(item_format, str) or item_format not in FORMATS | {"Any"}:
            raise ValueError("Choose a supported activity format.")
        minutes, count = payload.get("max_minutes", 30), payload.get("count", 5)
        if type(minutes) is not int or not 5 <= minutes <= 120:
            raise ValueError("Available time must be between 5 and 120 minutes.")
        if type(count) is not int or not 1 <= count <= 8:
            raise ValueError("Request between 1 and 8 activities.")
        diversity = payload.get("diversity", 0.25)
        if (type(diversity) not in (int, float) or not math.isfinite(diversity)
                or not 0 <= diversity <= 0.7):
            raise ValueError("Variety must be between 0 and 0.7.")
        return Preferences(query.strip(), topics, minutes, level, item_format,
                           liked, hidden, count, float(diversity))

    def recommend(self, payload: Any) -> dict[str, Any]:
        prefs = self.parse_preferences(payload)
        query = self.vectorizer.transform([" ".join((prefs.query, *prefs.topics))])
        seeds = [self.id_to_index[item_id] for item_id in prefs.liked_ids]
        if seeds:
            centroid = csr_matrix(self.matrix[seeds].mean(axis=0))
            # These profile weights are design choices, not trained parameters.
            query = (0.65 * query + 0.35 * centroid) if query.nnz else centroid
        profile = normalize(query, norm="l2").tocsr()
        personalized = bool(profile.nnz)
        excluded = frozenset(prefs.liked_ids) | frozenset(prefs.hidden_ids)
        eligible = [i for i, item in enumerate(self.activities)
                    if item.id not in excluded
                    and item.duration_minutes <= prefs.max_minutes
                    and (prefs.level == "Any" or item.level == prefs.level)
                    and (prefs.format == "Any" or item.format == prefs.format)]
        similarities = (cosine_similarity(self.matrix, profile).ravel()
                        if personalized else np.zeros(len(self.activities)))
        # Do not pad a personalized list with zero overlap items.
        candidates = [i for i in eligible if not personalized or similarities[i] > 1e-12]
        notice = "Recommendations reflect your current interests and filters."
        if not personalized:
            notice = ("Starter suggestions: no known interest terms matched. Try usability, "
                      "Python or a topic, or choose an activity you like.")
        if not candidates:
            notice = ("No activities match these choices. Increase available time, choose "
                      "Any difficulty or format, or change your interests.")
        selected: list[int] = []
        penalties: dict[int, float] = {}
        if not personalized:
            selected = sorted(candidates, key=lambda i: (self.activities[i].duration_minutes,
                                                          self.activities[i].id))[:prefs.count]
        else:
            remaining = set(candidates)
            while remaining and len(selected) < prefs.count:
                # Penalize overlap with already selected activities to add variety.
                redundancy = {i: float(cosine_similarity(
                    self.matrix[i], self.matrix[selected]).max()) if selected else 0.0
                    for i in remaining}
                chosen = min(remaining, key=lambda i: (
                    -(float(similarities[i]) - prefs.diversity * redundancy[i]),
                    -float(similarities[i]), self.activities[i].id))
                penalties[chosen] = prefs.diversity * redundancy[chosen]
                selected.append(chosen)
                remaining.remove(chosen)
        results = []
        for rank, index in enumerate(selected, start=1):
            item = self.activities[index]
            contributions = self.matrix[index].multiply(profile).tocsr()
            terms = sorted(zip(contributions.indices, contributions.data),
                           key=lambda pair: (-pair[1], self.feature_names[pair[0]]))[:3]
            matched = [str(self.feature_names[i]) for i, _ in terms]
            reasons = (["Shared profile terms: " + ", ".join(matched) + "."]
                       if personalized else ["Starter activity ordered by shorter duration."])
            reasons.append(f"Fits your {prefs.max_minutes} minute limit.")
            if prefs.level != "Any":
                reasons.append(f"Matches {prefs.level.lower()} difficulty.")
            if prefs.format != "Any":
                reasons.append(f"Matches your {prefs.format.lower()} format.")
            results.append({**asdict(item), "rank": rank,
                            "similarity": round(float(similarities[index]), 4)
                            if personalized else None,
                            "diversity_penalty": round(penalties.get(index, 0.0), 4),
                            "matched_terms": matched, "reasons": reasons})
        return {"mode": "personalized" if personalized else "starter",
                "notice": notice, "candidate_count": len(candidates),
                "results": results, "preferences": asdict(prefs)}

    def catalogue(self) -> dict[str, Any]:
        return {"activities": [asdict(item) for item in self.activities],
                "topics": list(self.topics), "levels": sorted(LEVELS),
                "formats": sorted(FORMATS)}
