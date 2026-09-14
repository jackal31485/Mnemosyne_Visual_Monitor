"""Phase 12B deterministic near-duplicate detection.

Near-duplicate detection identifies observations that may represent the same
underlying information while preserving both source observations.

Detection is a signal only.  It never performs or authorizes consolidation.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re

from src.domain.observation_similarity import (
    ObservationReference,
    ObservationSimilarity,
    ObservationSimilarityPolicy,
    ObservationSimilaritySignals,
    ObservationSimilarityResult,
)


def _required_text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} cannot be empty")
    return value.strip()


def _score(name: str, value: float) -> float:
    if not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")

    value = float(value)

    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0")

    return value


def normalize_observation_text(text: str) -> str:
    """Normalize text for deterministic comparison only.

    The original observation is never modified.
    """
    text = _required_text("text", text).casefold()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


def token_jaccard(left: str, right: str) -> float:
    """Return deterministic token-set similarity."""
    left_tokens = set(normalize_observation_text(left).split())
    right_tokens = set(normalize_observation_text(right).split())

    if not left_tokens and not right_tokens:
        return 1.0

    if not left_tokens or not right_tokens:
        return 0.0

    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def sequence_similarity(left: str, right: str) -> float:
    """Return deterministic normalized sequence similarity."""
    return SequenceMatcher(
        None,
        normalize_observation_text(left),
        normalize_observation_text(right),
        autojunk=False,
    ).ratio()


@dataclass(frozen=True)
class NearDuplicatePolicy:
    """Deterministic thresholds for near-duplicate classification."""

    exact_threshold: float = 1.0
    near_duplicate_threshold: float = 0.88
    token_threshold: float = 0.75

    def __post_init__(self) -> None:
        for name in (
            "exact_threshold",
            "near_duplicate_threshold",
            "token_threshold",
        ):
            _score(name, getattr(self, name))

        if self.near_duplicate_threshold > self.exact_threshold:
            raise ValueError(
                "near_duplicate_threshold cannot exceed exact_threshold"
            )


@dataclass(frozen=True)
class NearDuplicateResult:
    """Read-only result of comparing two observation texts."""

    left: ObservationReference
    right: ObservationReference
    left_text_hash: str
    right_text_hash: str
    normalized_text_similarity: float
    token_similarity: float
    similarity_result: ObservationSimilarityResult
    is_exact_duplicate: bool
    is_near_duplicate: bool
    reasons: frozenset[str]

    def __post_init__(self) -> None:
        _score(
            "normalized_text_similarity",
            self.normalized_text_similarity,
        )
        _score("token_similarity", self.token_similarity)

        if not isinstance(self.is_exact_duplicate, bool):
            raise TypeError("is_exact_duplicate must be a bool")

        if not isinstance(self.is_near_duplicate, bool):
            raise TypeError("is_near_duplicate must be a bool")

        if not isinstance(self.reasons, frozenset):
            object.__setattr__(
                self,
                "reasons",
                frozenset(self.reasons),
            )


class NearDuplicateDetector:
    """Detect exact and near-duplicate observations deterministically."""

    def __init__(
        self,
        policy: NearDuplicatePolicy | None = None,
        similarity_policy: ObservationSimilarityPolicy | None = None,
    ) -> None:
        self.policy = policy or NearDuplicatePolicy()
        self._similarity = ObservationSimilarity(
            similarity_policy,
        )

    @staticmethod
    def _text_hash(text: str) -> str:
        import hashlib

        return hashlib.sha256(
            normalize_observation_text(text).encode("utf-8")
        ).hexdigest()

    def compare(
        self,
        *,
        left: ObservationReference,
        right: ObservationReference,
        left_text: str,
        right_text: str,
        signals: ObservationSimilaritySignals | None = None,
    ) -> NearDuplicateResult:
        if not isinstance(left, ObservationReference):
            raise TypeError("left must be an ObservationReference")

        if not isinstance(right, ObservationReference):
            raise TypeError("right must be an ObservationReference")

        left_normalized = normalize_observation_text(left_text)
        right_normalized = normalize_observation_text(right_text)

        if not left_normalized or not right_normalized:
            raise ValueError("observation text cannot be empty")

        left_hash = self._text_hash(left_text)
        right_hash = self._text_hash(right_text)

        text_similarity = sequence_similarity(
            left_normalized,
            right_normalized,
        )
        token_similarity = token_jaccard(
            left_normalized,
            right_normalized,
        )

        if signals is None:
            signals = ObservationSimilaritySignals(
                normalized_text=text_similarity,
                semantic=0.0,
                shared_entities=0.0,
                shared_relationships=0.0,
                temporal_compatibility=1.0,
                shared_evidence=0.0,
                profile_overlap=(
                    1.0
                    if left.source_profile == right.source_profile
                    else 0.0
                ),
                explicit_identifier=0.0,
                observation_type=0.0,
                confidence=0.0,
                provenance=(
                    1.0
                    if left.source_profile and right.source_profile
                    else 0.0
                ),
            )
        else:
            signals = ObservationSimilaritySignals(
                normalized_text=text_similarity,
                semantic=signals.semantic,
                shared_entities=signals.shared_entities,
                shared_relationships=signals.shared_relationships,
                temporal_compatibility=signals.temporal_compatibility,
                shared_evidence=signals.shared_evidence,
                profile_overlap=signals.profile_overlap,
                explicit_identifier=signals.explicit_identifier,
                observation_type=signals.observation_type,
                confidence=signals.confidence,
                provenance=signals.provenance,
            )

        similarity_result = self._similarity.compare(
            left,
            right,
            signals,
        )

        exact = (
            left_hash == right_hash
            or (
                text_similarity >= self.policy.exact_threshold
                and token_similarity >= self.policy.token_threshold
            )
        )

        near_duplicate = (
            not exact
            and text_similarity >= self.policy.near_duplicate_threshold
            and token_similarity >= self.policy.token_threshold
        )

        reasons: set[str] = set()

        if exact:
            reasons.add("normalized_text_exact")

        if near_duplicate:
            reasons.add("normalized_text_near_duplicate")

        if token_similarity >= self.policy.token_threshold:
            reasons.add("token_overlap")

        if similarity_result.is_candidate:
            reasons.add("similarity_candidate_signal")

        return NearDuplicateResult(
            left=left,
            right=right,
            left_text_hash=left_hash,
            right_text_hash=right_hash,
            normalized_text_similarity=text_similarity,
            token_similarity=token_similarity,
            similarity_result=similarity_result,
            is_exact_duplicate=exact,
            is_near_duplicate=near_duplicate,
            reasons=frozenset(reasons),
        )
