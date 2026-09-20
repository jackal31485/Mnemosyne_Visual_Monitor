"""Application-level construction of Mnemosyne's production hybrid retriever."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from src.domain.collective import CollectiveDAO
from src.domain.graph_aggregator import GraphAggregator
from src.domain.live_memory_gateway import LiveMemoryGateway
from src.domain.temporal_evidence import TemporalEvidenceDAO
from src.domain.embedding_generator import SentenceTransformerEncoder
from src.retrieval.cross_encoder import LocalCrossEncoder
from src.retrieval.graph_search import GraphSearcher
from src.retrieval.hybrid_search import HybridRetrievalService
from src.retrieval.keyword_search import KeywordSearcher
from src.retrieval.rank_fusion import RankFusion
from src.retrieval.reranker import Reranker
from src.retrieval.semantic_search import SemanticSearcher
from src.retrieval.temporal_search import TemporalSearcher

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COLLECTIVE_DB = PROJECT_ROOT / "data" / "collective.db"
RETRIEVAL_DB = PROJECT_ROOT / "data" / "retrieval.db"
EMBEDDING_MODEL = PROJECT_ROOT / "models" / "all-MiniLM-L6-v2"
CROSS_ENCODER_MODEL = PROJECT_ROOT / "models" / "cross-encoder-ms-marco-MiniLM-L6-v2"


def build_hybrid_retrieval_service() -> HybridRetrievalService:
    """Build the production hybrid service from authoritative local stores.

    Model-heavy dependencies are constructed once by the cached application
    dependency rather than once per browser query.
    """
    dao = CollectiveDAO(COLLECTIVE_DB)
    dao.ensure_schema()

    gateway = LiveMemoryGateway()
    encoder = SentenceTransformerEncoder(
        model_path=EMBEDDING_MODEL,
        device=os.getenv("MNEMOSYNE_EMBEDDING_DEVICE", "cpu"),
    )

    reranker = None
    if os.getenv("MNEMOSYNE_HYBRID_RERANK", "1").strip().lower() not in {
        "0", "false", "no", "off",
    }:
        try:
            cross_encoder = LocalCrossEncoder(
                model_path=CROSS_ENCODER_MODEL,
                device=os.getenv("MNEMOSYNE_RERANK_DEVICE", "cpu"),
            )
            reranker = Reranker(cross_encoder, gateway)
        except (FileNotFoundError, ImportError):
            # Reranking is explicitly optional. Base hybrid retrieval remains
            # available when the optional local CrossEncoder is absent.
            reranker = None

    return HybridRetrievalService(
        keyword_searcher=KeywordSearcher(dao, db_path=RETRIEVAL_DB),
        semantic_searcher=SemanticSearcher(dao),
        graph_searcher=GraphSearcher(
            dao,
            GraphAggregator([dao], similarity_threshold=0.75),
        ),
        temporal_searcher=TemporalSearcher(dao, gateway),
        fusion=RankFusion(),
        encoder=encoder,
        reranker=reranker,
        evidence_dao=TemporalEvidenceDAO(COLLECTIVE_DB),
    )


@lru_cache(maxsize=1)
def get_hybrid_retrieval_service() -> HybridRetrievalService:
    """Return the process-local production hybrid service singleton."""
    return build_hybrid_retrieval_service()
