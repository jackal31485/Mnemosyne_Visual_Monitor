from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np

from src.domain.collective import CollectiveDAO
from src.domain.embedding_generator import SentenceTransformerEncoder
from src.domain.graph_aggregator import GraphAggregator
from src.domain.live_memory_gateway import LiveMemoryGateway
from src.retrieval.cross_encoder import LocalCrossEncoder
from src.retrieval.graph_search import GraphSearcher
from src.retrieval.keyword_search import KeywordSearcher
from src.retrieval.rank_fusion import RankFusion
from src.retrieval.reranker import Reranker
from src.retrieval.semantic_search import SemanticSearcher


ROOT = Path(__file__).resolve().parents[1]
EVAL_PATH = ROOT / "docs" / "phase_8f_evaluation_set.json"

CANDIDATE_LIMIT = 20
CHANNEL_LIMIT = 20
TOP_K = 10


def metric_recall(results, relevant, k):
    retrieved = {result.entry_id for result in results[:k]}
    relevant_set = set(relevant)

    if not relevant_set:
        return 0.0

    return len(retrieved & relevant_set) / len(relevant_set)


def metric_mrr(results, relevant, k):
    relevant_set = set(relevant)

    for rank, result in enumerate(results[:k], start=1):
        if result.entry_id in relevant_set:
            return 1.0 / rank

    return 0.0


def evaluate_query(results, relevant):
    return {
        "recall_at_5": metric_recall(results, relevant, 5),
        "recall_at_10": metric_recall(results, relevant, 10),
        "mrr_at_5": metric_mrr(results, relevant, 5),
        "mrr_at_10": metric_mrr(results, relevant, 10),
    }


def average_metrics(rows):
    if not rows:
        return {
            "recall_at_5": 0.0,
            "recall_at_10": 0.0,
            "mrr_at_5": 0.0,
            "mrr_at_10": 0.0,
        }

    keys = (
        "recall_at_5",
        "recall_at_10",
        "mrr_at_5",
        "mrr_at_10",
    )

    return {
        key: sum(row[key] for row in rows) / len(rows)
        for key in keys
    }


def main():
    evaluation = json.loads(EVAL_PATH.read_text())

    if not evaluation.get("frozen"):
        raise RuntimeError("Evaluation set must be frozen")

    if evaluation.get("phase_8_memories_included"):
        raise RuntimeError(
            "Evaluation set incorrectly includes Phase 8 memories"
        )

    dao = CollectiveDAO("data/collective.db")
    gateway = LiveMemoryGateway()

    keyword = KeywordSearcher(
        dao,
        db_path="data/retrieval.db",
    )

    embedding = SentenceTransformerEncoder(
        model_path="models/all-MiniLM-L6-v2",
        device="cuda",
    )

    semantic = SemanticSearcher(dao)

    graph_aggregator = GraphAggregator([dao], similarity_threshold=0.75)
    graph = GraphSearcher(
        dao,
        graph_aggregator,
    )

    fusion = RankFusion()

    cross_encoder = LocalCrossEncoder(
        model_path="models/cross-encoder-ms-marco-MiniLM-L6-v2",
        device="cuda",
    )

    reranker = Reranker(
        cross_encoder,
        gateway,
    )

    baseline_rows = []
    reranked_rows = []
    details = []

    try:
        for item in evaluation["queries"]:
            query_id = item["id"]
            query = item["query"]
            relevant = item["relevant"]

            print()
            print("=" * 72)
            print(f"{query_id}: {query}")
            print("=" * 72)

            # Keyword channel.
            keyword_results = keyword.search(
                query,
                limit=CHANNEL_LIMIT,
            )

            # Semantic channel.
            query_vector = np.frombuffer(
                embedding.generate(query),
                dtype=np.float32,
            )

            semantic_results = semantic.search(
                query_vector,
                top_k=CHANNEL_LIMIT,
            )

            # Graph channel.
            #
            # Graph retrieval requires explicit seeds. For evaluation,
            # use the union of the first-ranked lexical and semantic
            # candidates as discovery seeds. This does not expand the
            # candidate pool beyond the graph channel's bounded output.
            seed_ids = []
            for result in (
                keyword_results[:5] +
                semantic_results[:5]
            ):
                if result.entry_id not in seed_ids:
                    seed_ids.append(result.entry_id)

            graph_results = graph.expand(
                seed_ids,
                limit_per_seed=4,
            )

            fused = fusion.fuse(
                keyword_results=keyword_results,
                semantic_results=semantic_results,
                graph_results=graph_results,
                temporal_results=(),
                top_k=CANDIDATE_LIMIT,
            )

            baseline = fused[:TOP_K]

            reranked = reranker.rerank(
                query,
                fused,
                candidate_limit=CANDIDATE_LIMIT,
                top_k=TOP_K,
            )

            baseline_metrics = evaluate_query(
                baseline,
                relevant,
            )

            reranked_metrics = evaluate_query(
                reranked,
                relevant,
            )

            baseline_rows.append(baseline_metrics)
            reranked_rows.append(reranked_metrics)

            print("Relevant:", relevant)

            print("\n8E RRF top 10:")
            for rank, result in enumerate(baseline, start=1):
                marker = "*" if result.entry_id in relevant else " "
                print(
                    f"{marker} {rank:2d} "
                    f"id={result.entry_id:<5d} "
                    f"score={result.fused_score:.6f}"
                )

            print("\n8F RRF + CrossEncoder top 10:")
            for result in reranked:
                marker = "*" if result.entry_id in relevant else " "
                print(
                    f"{marker} {result.reranker_rank:2d} "
                    f"id={result.entry_id:<5d} "
                    f"reranker={result.reranker_score: .6f} "
                    f"rrf={result.fused_score:.6f}"
                )

            print(
                "\n8E:",
                baseline_metrics,
            )
            print(
                "8F:",
                reranked_metrics,
            )

            details.append(
                {
                    "id": query_id,
                    "query": query,
                    "relevant": relevant,
                    "baseline": [
                        {
                            "entry_id": result.entry_id,
                            "rank": rank,
                            "fused_score": result.fused_score,
                        }
                        for rank, result in enumerate(
                            baseline,
                            start=1,
                        )
                    ],
                    "reranked": [
                        {
                            "entry_id": result.entry_id,
                            "rank": result.reranker_rank,
                            "reranker_score": result.reranker_score,
                            "fused_score": result.fused_score,
                        }
                        for result in reranked
                    ],
                    "baseline_metrics": baseline_metrics,
                    "reranked_metrics": reranked_metrics,
                }
            )

    finally:
        keyword.close()
        dao.close()

    baseline_average = average_metrics(baseline_rows)
    reranked_average = average_metrics(reranked_rows)

    print()
    print("=" * 72)
    print("PHASE 8F EVALUATION SUMMARY")
    print("=" * 72)

    print("\n8E RRF baseline:")
    for key, value in baseline_average.items():
        print(f"  {key}: {value:.4f}")

    print("\n8F RRF + CrossEncoder:")
    for key, value in reranked_average.items():
        print(f"  {key}: {value:.4f}")

    print("\nDelta:")
    for key in baseline_average:
        delta = reranked_average[key] - baseline_average[key]
        print(f"  {key}: {delta:+.4f}")

    output = {
        "evaluation_version": evaluation["version"],
        "queries": len(evaluation["queries"]),
        "phase_8_memories_included": False,
        "candidate_limit": CANDIDATE_LIMIT,
        "top_k": TOP_K,
        "baseline": baseline_average,
        "reranked": reranked_average,
        "delta": {
            key: reranked_average[key] - baseline_average[key]
            for key in baseline_average
        },
        "details": details,
    }

    output_path = ROOT / "docs" / "phase_8f_evaluation_results.json"
    output_path.write_text(
        json.dumps(
            output,
            indent=2,
        )
        + "\n"
    )

    print()
    print(f"Detailed results written to {output_path}")


if __name__ == "__main__":
    main()
