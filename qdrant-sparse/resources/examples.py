"""
Qdrant Sparse Vector — Working Examples (qdrant-client >= 1.17)
================================================================

Lean examples focused on correctness and performance.
Requires: pip install qdrant-client numpy
"""

from __future__ import annotations

import numpy as np
from qdrant_client import QdrantClient, models

# ---------------------------------------------------------------------------
# Conversion helpers — performance-oriented, numpy-backed
# ---------------------------------------------------------------------------


def to_sparse(sparse_dict: dict[int, float]) -> models.SparseVector:
    """Convert {index: value} dict to SparseVector. Zero-alloc for empty."""
    if not sparse_dict:
        return models.SparseVector(indices=[], values=[])
    idx = np.fromiter(sparse_dict.keys(), dtype=np.int32, count=len(sparse_dict))
    val = np.fromiter(sparse_dict.values(), dtype=np.float32, count=len(sparse_dict))
    return models.SparseVector(indices=idx.tolist(), values=val.tolist())


def prune_topk(sv: models.SparseVector, k: int = 64) -> models.SparseVector:
    """Keep top-k by magnitude. Reduces query latency (fewer non-zeros = faster)."""
    if len(sv.indices) <= k:
        return sv
    vals = np.array(sv.values, dtype=np.float32)
    topk_idx = np.argpartition(np.abs(vals), -k)[-k:]  # O(n) partial sort
    return models.SparseVector(
        indices=[sv.indices[i] for i in topk_idx],
        values=[sv.values[i] for i in topk_idx],
    )


# ---------------------------------------------------------------------------
# Example 1: Sparse-only collection with IDF
# ---------------------------------------------------------------------------


def example_sparse_collection():
    """Minimal sparse collection: create, upsert, search, filter."""
    client = QdrantClient(":memory:")

    client.create_collection(
        collection_name="docs",
        vectors_config={},
        sparse_vectors_config={
            "text": models.SparseVectorParams(modifier=models.Modifier.IDF)
        },
    )

    # Batch upsert — always use batches for throughput
    client.upsert(
        collection_name="docs",
        points=[
            models.PointStruct(
                id=i,
                payload={"text": text, "lang": lang},
                vector={"text": to_sparse(sv)},
            )
            for i, (text, lang, sv) in enumerate(
                [
                    ("Machine learning overview", "en", {10: 0.8, 42: 0.6, 100: 0.9}),
                    ("Deep neural networks", "en", {10: 0.7, 55: 0.5, 300: 0.85}),
                    ("Procesamiento de lenguaje natural", "es", {42: 0.4, 77: 0.9}),
                    ("Computer vision and images", "en", {55: 0.3, 88: 0.8, 500: 0.5}),
                ]
            )
        ],
    )

    # Search
    results = client.query_points(
        collection_name="docs",
        query=to_sparse({10: 0.9, 42: 0.5}),
        using="text",
        limit=3,
    ).points

    # Search with payload filter
    filtered = client.query_points(
        collection_name="docs",
        query=to_sparse({10: 0.9, 42: 0.5}),
        using="text",
        query_filter=models.Filter(
            must=[models.FieldCondition(key="lang", match=models.MatchValue(value="en"))]
        ),
        limit=3,
    ).points

    print("=== Sparse Search ===")
    for r in results:
        print(f"  id={r.id}  score={r.score:.4f}")
    print(f"\n  Filtered (lang=en): {len(filtered)} results")
    return results


# ---------------------------------------------------------------------------
# Example 2: Hybrid search (dense + sparse) with RRF / DBSF
# ---------------------------------------------------------------------------


def example_hybrid_search():
    """Hybrid dense+sparse with both fusion strategies."""
    client = QdrantClient(":memory:")

    client.create_collection(
        collection_name="hybrid",
        vectors_config={
            "dense": models.VectorParams(size=4, distance=models.Distance.COSINE)
        },
        sparse_vectors_config={
            "sparse": models.SparseVectorParams(modifier=models.Modifier.IDF)
        },
    )

    client.upsert(
        collection_name="hybrid",
        points=[
            models.PointStruct(
                id=1,
                payload={"text": "Quantum computing"},
                vector={
                    "dense": [0.1, 0.2, 0.3, 0.4],
                    "sparse": models.SparseVector(indices=[10, 20], values=[0.9, 0.5]),
                },
            ),
            models.PointStruct(
                id=2,
                payload={"text": "Classical computing"},
                vector={
                    "dense": [0.8, 0.7, 0.6, 0.5],
                    "sparse": models.SparseVector(indices=[10, 40], values=[0.4, 0.8]),
                },
            ),
        ],
    )

    dense_q = [0.12, 0.22, 0.32, 0.42]
    sparse_q = models.SparseVector(indices=[10, 20], values=[0.9, 0.6])

    prefetches = [
        models.Prefetch(query=dense_q, using="dense", limit=10),
        models.Prefetch(query=sparse_q, using="sparse", limit=10),
    ]

    # RRF fusion (v1.10+) — rank-based, robust default
    rrf = client.query_points(
        collection_name="hybrid",
        prefetch=prefetches,
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=3,
    ).points

    # Parameterized RRF (v1.16+) — tune k constant
    rrf_k = client.query_points(
        collection_name="hybrid",
        prefetch=prefetches,
        query=models.RrfQuery(rrf=models.Rrf(k=60)),
        limit=3,
    ).points

    # DBSF fusion — score-based, better when score distributions are comparable
    dbsf = client.query_points(
        collection_name="hybrid",
        prefetch=prefetches,
        query=models.FusionQuery(fusion=models.Fusion.DBSF),
        limit=3,
    ).points

    print("=== Hybrid Search ===")
    print(f"  RRF:      {[(r.id, round(r.score, 4)) for r in rrf]}")
    print(f"  RRF(k=60):{[(r.id, round(r.score, 4)) for r in rrf_k]}")
    print(f"  DBSF:     {[(r.id, round(r.score, 4)) for r in dbsf]}")
    return rrf


# ---------------------------------------------------------------------------
# Example 3: Performance — on-disk index, float16, pruning
# ---------------------------------------------------------------------------


def example_performance_config():
    """Production config for large collections: on-disk index + float16."""
    client = QdrantClient(":memory:")

    client.create_collection(
        collection_name="perf",
        vectors_config={},
        sparse_vectors_config={
            "text": models.SparseVectorParams(
                modifier=models.Modifier.IDF,
                index=models.SparseIndexParams(
                    on_disk=True,        # Keep inverted index on disk for large collections
                    datatype=models.Datatype.FLOAT16,  # Half memory, negligible quality loss
                ),
            )
        },
    )

    # Pruning reduces query latency at minor quality cost
    raw = models.SparseVector(
        indices=list(range(200)),
        values=[float(i) * 0.01 for i in range(200)],
    )
    pruned = prune_topk(raw, k=32)
    print(f"=== Performance ===")
    print(f"  Raw: {len(raw.indices)} dims -> Pruned: {len(pruned.indices)} dims")
    print(f"  On-disk + float16 collection created")


# ---------------------------------------------------------------------------
# Run all
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    example_sparse_collection()
    print()
    example_hybrid_search()
    print()
    example_performance_config()
    print("\nAll examples passed.")
