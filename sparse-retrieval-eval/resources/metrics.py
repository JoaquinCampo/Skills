"""
Information Retrieval evaluation metrics for sparse retrieval.

Reference implementations of nDCG@k, Recall@k, MAP, MRR, and helpers.
All functions are pure Python + numpy, no external IR library required.
"""

from __future__ import annotations

import numpy as np


# ---------------------------------------------------------------------------
# Primitive helpers
# ---------------------------------------------------------------------------


def dcg_at_k(relevances: list[float], k: int) -> float:
    """Discounted Cumulative Gain at rank k.

    DCG@k = sum_{i=1}^{k} (2^{rel_i} - 1) / log2(i + 1)

    Args:
        relevances: Graded relevance values in retrieval order.
        k: Cutoff rank.

    Returns:
        DCG value (non-negative float).
    """
    dcg = 0.0
    for i, rel in enumerate(relevances[:k]):
        dcg += (2**rel - 1) / np.log2(i + 2)  # i+2 because i is 0-indexed
    return float(dcg)


# ---------------------------------------------------------------------------
# Per-query metrics
# ---------------------------------------------------------------------------


def ndcg_at_k(
    retrieved: list[tuple[str, float]],
    qrels: dict[str, int],
    k: int = 10,
) -> float:
    """Normalized Discounted Cumulative Gain at rank k.

    nDCG@k = DCG@k / IDCG@k

    Args:
        retrieved: List of (doc_id, score) tuples in decreasing score order.
        qrels: Mapping from doc_id to integer relevance grade.
        k: Cutoff rank (default 10).

    Returns:
        nDCG value in [0, 1].
    """
    # Actual relevances in retrieval order
    rels = [float(qrels.get(did, 0)) for did, _ in retrieved[:k]]
    # Ideal relevances (best possible ranking)
    ideal_rels = sorted(qrels.values(), reverse=True)[:k]
    ideal_rels_f = [float(r) for r in ideal_rels]

    dcg = dcg_at_k(rels, k)
    idcg = dcg_at_k(ideal_rels_f, k)
    return dcg / idcg if idcg > 0 else 0.0


def recall_at_k(
    retrieved_ids: list[str],
    relevant_ids: set[str],
    k: int,
) -> float:
    """Recall at rank k.

    Recall@k = |retrieved@k intersect relevant| / |relevant|

    Args:
        retrieved_ids: Document IDs in retrieval order.
        relevant_ids: Set of relevant document IDs.
        k: Cutoff rank.

    Returns:
        Recall value in [0, 1].
    """
    if not relevant_ids:
        return 0.0
    retrieved_set = set(retrieved_ids[:k])
    return len(retrieved_set & relevant_ids) / len(relevant_ids)


def average_precision(
    retrieved_ids: list[str],
    relevant_ids: set[str],
) -> float:
    """Average Precision for a single query.

    AP = (1/|relevant|) * sum_{k: doc_k is relevant} Precision@k

    Args:
        retrieved_ids: Document IDs in retrieval order.
        relevant_ids: Set of relevant document IDs.

    Returns:
        AP value in [0, 1].
    """
    if not relevant_ids:
        return 0.0
    hits = 0
    sum_precision = 0.0
    for i, did in enumerate(retrieved_ids):
        if did in relevant_ids:
            hits += 1
            sum_precision += hits / (i + 1)
    return sum_precision / len(relevant_ids)


def reciprocal_rank(
    retrieved_ids: list[str],
    relevant_ids: set[str],
) -> float:
    """Reciprocal Rank for a single query.

    RR = 1 / rank_of_first_relevant_doc  (0 if none found)

    Args:
        retrieved_ids: Document IDs in retrieval order.
        relevant_ids: Set of relevant document IDs.

    Returns:
        RR value in (0, 1] or 0.0 if no relevant doc is retrieved.
    """
    for i, did in enumerate(retrieved_ids):
        if did in relevant_ids:
            return 1.0 / (i + 1)
    return 0.0


# ---------------------------------------------------------------------------
# Aggregated (mean) metrics over a query set
# ---------------------------------------------------------------------------


def mean_ndcg_at_k(
    all_retrieved: dict[str, list[tuple[str, float]]],
    all_qrels: dict[str, dict[str, int]],
    k: int = 10,
) -> float:
    """Mean nDCG@k over all queries that have relevance judgments.

    Args:
        all_retrieved: {query_id: [(doc_id, score), ...]} in score-descending order.
        all_qrels: {query_id: {doc_id: relevance_grade}}.
        k: Cutoff rank.

    Returns:
        Mean nDCG@k across evaluated queries.
    """
    scores = []
    for qid, qrel in all_qrels.items():
        retrieved = all_retrieved.get(qid, [])
        scores.append(ndcg_at_k(retrieved, qrel, k))
    return float(np.mean(scores)) if scores else 0.0


def mean_recall_at_k(
    all_retrieved: dict[str, list[tuple[str, float]]],
    all_qrels: dict[str, dict[str, int]],
    k: int = 100,
) -> float:
    """Mean Recall@k over all queries that have relevance judgments.

    Args:
        all_retrieved: {query_id: [(doc_id, score), ...]}.
        all_qrels: {query_id: {doc_id: relevance_grade}}.
        k: Cutoff rank.

    Returns:
        Mean Recall@k.
    """
    scores = []
    for qid, qrel in all_qrels.items():
        retrieved = all_retrieved.get(qid, [])
        ids = [did for did, _ in retrieved]
        relevant = {did for did, rel in qrel.items() if rel > 0}
        scores.append(recall_at_k(ids, relevant, k))
    return float(np.mean(scores)) if scores else 0.0


def mean_average_precision(
    all_retrieved: dict[str, list[tuple[str, float]]],
    all_qrels: dict[str, dict[str, int]],
) -> float:
    """Mean Average Precision (MAP) over all queries.

    Args:
        all_retrieved: {query_id: [(doc_id, score), ...]}.
        all_qrels: {query_id: {doc_id: relevance_grade}}.

    Returns:
        MAP value.
    """
    scores = []
    for qid, qrel in all_qrels.items():
        retrieved = all_retrieved.get(qid, [])
        ids = [did for did, _ in retrieved]
        relevant = {did for did, rel in qrel.items() if rel > 0}
        scores.append(average_precision(ids, relevant))
    return float(np.mean(scores)) if scores else 0.0


def mean_reciprocal_rank(
    all_retrieved: dict[str, list[tuple[str, float]]],
    all_qrels: dict[str, dict[str, int]],
) -> float:
    """Mean Reciprocal Rank (MRR) over all queries.

    Args:
        all_retrieved: {query_id: [(doc_id, score), ...]}.
        all_qrels: {query_id: {doc_id: relevance_grade}}.

    Returns:
        MRR value.
    """
    scores = []
    for qid, qrel in all_qrels.items():
        retrieved = all_retrieved.get(qid, [])
        ids = [did for did, _ in retrieved]
        relevant = {did for did, rel in qrel.items() if rel > 0}
        scores.append(reciprocal_rank(ids, relevant))
    return float(np.mean(scores)) if scores else 0.0


# ---------------------------------------------------------------------------
# Full evaluation convenience function
# ---------------------------------------------------------------------------


def evaluate_retrieval(
    all_retrieved: dict[str, list[tuple[str, float]]],
    all_qrels: dict[str, dict[str, int]],
    k_values: list[int] | None = None,
) -> dict[str, float]:
    """Run full IR evaluation and return a metrics dictionary.

    Args:
        all_retrieved: {query_id: [(doc_id, score), ...]} sorted by score desc.
        all_qrels: {query_id: {doc_id: relevance_grade}}.
        k_values: Cutoff values for nDCG and Recall (default [1, 5, 10, 100]).

    Returns:
        Dictionary with keys like "nDCG@10", "Recall@100", "MAP", "MRR".
    """
    if k_values is None:
        k_values = [1, 5, 10, 100]

    results: dict[str, float] = {}

    for k in k_values:
        results[f"nDCG@{k}"] = mean_ndcg_at_k(all_retrieved, all_qrels, k)
        results[f"Recall@{k}"] = mean_recall_at_k(all_retrieved, all_qrels, k)

    results["MAP"] = mean_average_precision(all_retrieved, all_qrels)
    results["MRR"] = mean_reciprocal_rank(all_retrieved, all_qrels)

    return results
