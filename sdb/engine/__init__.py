"""The deterministic discovery engine: traverse → score surprise → rank by trust → narrate."""

from sdb.engine.confidence import TrustScore, noisy_or, score_trust, statement_confidence
from sdb.engine.narrate import narrate
from sdb.engine.pipeline import TopicNotFoundError, discover
from sdb.engine.surprise import SurpriseScore, score_surprise
from sdb.engine.traversal import enumerate_paths

__all__ = [
    "SurpriseScore",
    "TopicNotFoundError",
    "TrustScore",
    "discover",
    "enumerate_paths",
    "narrate",
    "noisy_or",
    "score_surprise",
    "score_trust",
    "statement_confidence",
]
