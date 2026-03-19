# miniCOIL Architecture Reference

Detailed architecture diagrams and data flow for the miniCOIL sparse neural retrieval model.

## System Architecture Overview

```
                          miniCOIL v1 System Architecture
  ============================================================================

  TRAINING TIME (offline, per-word)
  ------------------------------------

  OpenWebText (40M sentences)    English Word List
        |                              |
        v                              v
  +-------------+            +--------------------+
  | Extract     |            | Build Word         |
  | Sentences   |            | Vocabulary         |
  | (~8k/word)  |            | (30k common words) |
  +-------------+            +--------------------+
        |                              |
        v                              v
  +------------------------------------------+
  |          Per-Word Training                |
  |                                          |
  |  For each word:                          |
  |                                          |
  |  1. Fetch sentences containing word      |
  |  2. Encode with jina-embed (512D)        |
  |  3. Encode with mxbai-large (1024D)      |
  |  4. Mine semi-hard triplets              |
  |  5. Train Linear(512,4) + tanh           |
  |  6. Save weight + bias                   |
  +------------------------------------------+
                   |
                   v
          word_layers.pt
          (30,000 trained layers)


  INFERENCE TIME (per query/document)
  ------------------------------------

  Input Text -----> Tokenize -----> Look up words
       |                                  |
       v                                  v
  jina-embed (512D)              Matched word indices
       |                                  |
       v                                  v
  Dense embedding         For each word: tanh(W @ emb + b) -> 4D
       |                                  |
       +----------------------------------+
                      |
                      v
              Sparse Vector
         {word_index*4+offset: value}
                      |
              +-------+-------+
              |               |
              v               v
         Qdrant IDF      scipy CSR
        (production)    (evaluation)
```

## Triplet Mining Flow

```
  For word "bat" (word index 42):
  ======================================

  Sentences in DB:
  +----+--------------------------------------------------+
  | #  | Sentence                                         |
  +----+--------------------------------------------------+
  |  0 | "The bat flew out of the cave at dusk"           |
  |  1 | "A fruit bat hung upside down from the tree"     |
  |  2 | "He swung the bat and hit a home run"            |
  |  3 | "She picked up the baseball bat"                 |
  |  4 | "The bat colony lived under the bridge"          |
  | .. | ...                                              |
  +----+--------------------------------------------------+

  Step 1: Encode all sentences with mining encoder (mxbai-embed-large-v1, 1024D)
          Compute pairwise cosine similarity matrix

          Similarity Matrix (mining embeddings):
              #0    #1    #2    #3    #4
          #0 [1.00  0.85  0.31  0.28  0.91]
          #1 [0.85  1.00  0.25  0.22  0.82]
          #2 [0.31  0.25  1.00  0.92  0.29]
          #3 [0.28  0.22  0.92  1.00  0.26]
          #4 [0.91  0.82  0.29  0.26  1.00]

  Step 2: For each triplet to mine:

          Anchor: randomly select sentence (e.g., #0, "bat flew out of cave")
                                        |
                  +---------+-----------+
                  |                     |
                  v                     v
          Top-20 most similar    Select positive
          [#4(0.91), #1(0.85),   Random from top-20
           #2(0.31), #3(0.28)]  -> #4 (sim=0.91)
                                        |
                  +--- Positive: #4 ---+
                  |                     |
                  v                     v
          Semi-hard negatives:       Fallback:
          sim < 0.91 AND > -1.5      least similar
          Candidates: #1(0.85),      overall
           #2(0.31), #3(0.28)
          Select closest: #1 (0.85)
                  |
                  v
          Negative: #1 (sim=0.85)

          Triplet: (anchor=#0, positive=#4, negative=#1)

  Step 3: Train with input encoder embeddings (not mining embeddings!)

          a_emb = input_embs[#0]   # 512D from jina-embeddings
          p_emb = input_embs[#4]   # 512D from jina-embeddings
          n_emb = input_embs[#1]   # 512D from jina-embeddings

          a_out = tanh(W @ a_emb + b)  # 4D
          p_out = tanh(W @ p_emb + b)  # 4D
          n_out = tanh(W @ n_emb + b)  # 4D

          loss = max(0, ||a_out - p_out|| - ||a_out - n_out|| + margin)
```

## Sparse Vector Format

```
  Text: "The cat sat on the mat"

  Step 1: Tokenize
  ["the", "cat", "sat", "on", "the", "mat"]

  Step 2: Word lookup (vocabulary)
  "cat" -> word index 42
  "mat" -> word index 1337
  Others: no vocabulary match (common words filtered out)

  Step 3: Encode full text with jina-embeddings-v2-small-en
  emb = jina("The cat sat on the mat")  # -> [512D]

  Step 4: Apply per-word linear layers

  Word 42 (cat):
    W_42 = [4 x 512]   (trained weight matrix)
    b_42 = [4]          (trained bias)
    out_42 = tanh(W_42 @ emb + b_42)  # -> [0.42, -0.31, 0.85, -0.12]

  Word 1337 (mat):
    W_1337 = [4 x 512]
    b_1337 = [4]
    out_1337 = tanh(W_1337 @ emb + b_1337)  # -> [0.15, 0.67, -0.43, 0.89]

  Step 5: Build sparse vector

  Index formula: word_index * 4 + offset

  Word 42: base = 42 * 4 = 168
    {168: 0.42, 169: -0.31, 170: 0.85, 171: -0.12}

  Word 1337: base = 1337 * 4 = 5348
    {5348: 0.15, 5349: 0.67, 5350: -0.43, 5351: 0.89}

  Final sparse vector (8 non-zero values out of 120,000 dimensions):
    {168: 0.42, 169: -0.31, 170: 0.85, 171: -0.12,
     5348: 0.15, 5349: 0.67, 5350: -0.43, 5351: 0.89}
```

## Training Loop Data Flow

```
  For each word (30,000 total):
  =============================

  Phase 1: Data Collection
  +---------------------------------------------------+
  | Fetch ~8,000 sentences containing this word       |
  | from OpenWebText training database                |
  +---------------------------------------------------+
       |
       v
  Phase 2: Encoding
  +---------------------------------------------------+
  | Input encoder (jina-embeddings-v2-small-en):      |
  |   input_embs = encode(sentences)  # [N, 512]     |
  |                                                   |
  | Mining encoder (mxbai-embed-large-v1):            |
  |   mining_embs = encode(sentences)  # [N, 1024]   |
  +---------------------------------------------------+
       |
       v
  Phase 3: Training
  +---------------------------------------------------+
  | 1. Mine triplets using mining_embs similarities   |
  |    (anchor, positive, negative) indices           |
  |                                                   |
  | 2. Train Linear(512, 4) + tanh                    |
  |    SGD, TripletMarginLoss(margin=0.3)             |
  |                                                   |
  | 3. Store weight [4,512] + bias [4]                |
  +---------------------------------------------------+
       |
       v
  Phase 4: Save
  +---------------------------------------------------+
  | Save to word_layers.pt                            |
  |   {word: {"weight": Tensor[4,512],                |
  |           "bias": Tensor[4]}}                     |
  +---------------------------------------------------+

  ~50 seconds per word on single CPU
  ~17 hours total for 30,000 words
```

## Evaluation Pipeline Data Flow

```
  Dataset (BEIR: NQ, Quora, FiQA, HotpotQA, MS MARCO)
       |
       +---> Corpus (documents)          Queries         QRels (ground truth)
       |         |                          |                    |
       |         v                          |                    |
       |  MiniCoilEncoder.encode_batch_sparse()                  |
       |         |                          |                    |
       |         v                          |                    |
       |  scipy CSR Matrix                  |                    |
       |  [n_docs x sparse_dim]             |                    |
       |         |                          |                    |
       |         v                          |                    |
       |  Compute IDF                       |                    |
       |  idf[j] = log(1 + (N-df+0.5)      |                    |
       |               / (df+0.5))          |                    |
       |         |                          |                    |
       |         v                          v                    |
       |     +------+    MiniCoilEncoder.encode_batch_sparse()   |
       |     | IDF  |         |                                  |
       |     +------+         |                                  |
       |         |            v                                  |
       |         v     Query sparse vectors                      |
       |                      |                                  |
       |     IDF-weighted dot product:                           |
       |     For each query q:                                   |
       |       q_idf = q_values * idf[q_indices]                 |
       |       scores = q_sparse_idf @ corpus_csr.T              |
       |       top_k = argpartition(scores, -k)[-k:]             |
       |                      |                                  |
       |                      v                                  v
       |               Retrieved docs  <------compare------> Relevant docs
       |                      |                                  |
       |                      v                                  |
       |                nDCG@10 per query                        |
       |                      |                                  |
       |                      v                                  |
       |              Mean nDCG@10                               |
       |                                                         |
       +--- Cache: corpus.npz, idf.npy, doc_ids.json -----------+
```

## Model Size Analysis

```
  Per-word model:
    Weight: [4 x 512] = 2,048 float32 values = 8,192 bytes
    Bias:   [4]        = 4 float32 values    = 16 bytes
    Total per word: 8,208 bytes (~8 KB)

  Full model (30,000 words):
    Weights: 30,000 x 2,048 = 61,440,000 params
    Biases:  30,000 x 4     = 120,000 params
    Total:   61,560,000 params (~235 MB as float32)

  For comparison:
    jina-embeddings encoder: 33M params (~126 MB)
    miniCOIL layers:         62M params (~235 MB)
    Total system:            95M params (~361 MB)

  Sparse vector per document:
    Average matched words: ~5-15 per document
    Non-zero values: words * 4 = 20-60 values
    Storage per doc: ~240-480 bytes (indices + values)
    vs dense 512D:   2,048 bytes
    Savings: 4-8x less storage per document
```

## File Structure and Data Artifacts

```
  data/
  +-- word_vocabulary.json              # 30,000 English words
  +-- word_layers.pt                    # Trained linear layers (30k words)
  +-- training_sentences.db             # Training sentences from OpenWebText

  Available as:
  +-- HuggingFace: Qdrant/minicoil-v1
  +-- FastEmbed: v0.7.0+
```

## Constants Quick Reference

```python
# Encoder models
INPUT_ENCODER = "jina-embeddings-v2-small-en"    # 512D, 33M params
MINING_ENCODER = "mxbai-embed-large-v1"          # 1024D
INPUT_DIM = 512
OUTPUT_DIM = 4

# Vocabulary
VOCAB_SIZE = 30000  # Most common English words (cleaned, stemmed, >3 chars)

# Sparse encoding
SPARSE_EPSILON = 1e-6           # Filter threshold for near-zero values

# Training
MARGIN = 0.3                    # Triplet loss margin
MIN_SENTENCES_PER_WORD = 10     # Skip words with fewer sentences
TRIPLET_TOPK = 20               # Top-K for positive selection
NEG_SIM_FLOOR = -1.5            # Floor for semi-hard negative mining
TRIPLETS_PER_SENTENCE_MULTIPLIER = 5  # Scale triplets by sentence count

# Training data
SENTENCES_PER_WORD = 8000       # ~8,000 sentences per word from OpenWebText
TRAINING_TIME_PER_WORD = 50     # ~50 seconds per word on single CPU

# Evaluation (BEIR benchmarks)
QUERY_ENCODE_BATCH = 256
# IDF formula: log(1 + (N - df + 0.5) / (df + 0.5))
```
