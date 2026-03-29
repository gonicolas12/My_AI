"""KV cache quantisation demo — simulates transformer attention with TurboQuant.

Run:  python -m turboquant.kv_cache_demo

Scenario:
  - 512 tokens, 8 attention heads, head_dim = 64
  - All key vectors quantised at 3 bits/dim with TurboQuantProd
  - Approximate attention scores compared against exact float32
  - Top-5 token agreement verified per head
"""

import sys
import os
import time
import numpy as np

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from turboquant import TurboQuantProd


def softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - np.max(x))
    return e / e.sum()


def main():
    # ----- Config -----
    n_tokens = 512
    n_heads = 8
    head_dim = 64
    bits = 3
    seed = 123

    print("=" * 56)
    print("  TurboQuant KV Cache Demo")
    print("=" * 56)
    print(f"\n  tokens={n_tokens}  heads={n_heads}  head_dim={head_dim}  bits={bits}\n")

    rng = np.random.default_rng(seed)

    # ----- Generate synthetic KV cache + query -----
    keys = rng.standard_normal((n_tokens, n_heads, head_dim))
    queries = rng.standard_normal((n_heads, head_dim))

    # ----- One quantiser per head (shared across tokens) -----
    tq_per_head = [
        TurboQuantProd(bits=bits, dim=head_dim, seed=42 + h) for h in range(n_heads)
    ]

    # ----- Quantise all keys -----
    t0 = time.perf_counter()
    quantized_keys: list[list] = []   # [head][token]
    for h in range(n_heads):
        head_qs = [tq_per_head[h].quantize(keys[t, h]) for t in range(n_tokens)]
        quantized_keys.append(head_qs)
    t_quant = time.perf_counter() - t0
    print(f"  Quantised {n_tokens * n_heads} key vectors in {t_quant:.3f}s\n")

    # ----- Compute attention scores -----
    top_k = 5
    all_match = True

    print(f"  {'Head':>4}  {'Corr':>8}  {'MaxErr':>9}  {'MeanErr':>9}  Top-{top_k} match")
    print(f"  {'----':>4}  {'----':>8}  {'------':>9}  {'-------':>9}  {'----------'}")

    for h in range(n_heads):
        q = queries[h]
        tq = tq_per_head[h]

        # Exact float32 scores
        scores_exact = keys[:, h, :] @ q                      # (n_tokens,)

        # TurboQuant approximate scores (batch API)
        scores_approx = tq.attention_scores(q, quantized_keys[h])

        # Metrics
        errors = scores_approx - scores_exact
        corr = np.corrcoef(scores_approx, scores_exact)[0, 1]
        max_err = np.max(np.abs(errors))
        mean_err = np.mean(np.abs(errors))

        top_exact = set(np.argsort(scores_exact)[-top_k:])
        top_approx = set(np.argsort(scores_approx)[-top_k:])
        match = top_exact == top_approx
        if not match:
            all_match = False

        tag = "YES" if match else "NO"
        print(f"  {h:4d}  {corr:8.5f}  {max_err:9.4f}  {mean_err:9.4f}  {tag}")

    # ----- Memory summary -----
    fp32_bytes = n_tokens * n_heads * head_dim * 4
    tq_bits_total = n_tokens * n_heads * TurboQuantProd.storage_bits(head_dim, bits)
    tq_bytes = tq_bits_total / 8
    ratio = fp32_bytes / tq_bytes

    print(f"\n  Memory")
    print(f"    float32:     {fp32_bytes:>10,} bytes")
    print(f"    TurboQuant:  {int(tq_bytes):>10,} bytes")
    print(f"    Ratio:       {ratio:>10.1f}x\n")

    # ----- Softmax attention comparison for head 0 -----
    h = 0
    q = queries[h]
    scale = 1.0 / np.sqrt(head_dim)
    scores_exact = keys[:, h, :] @ q * scale
    scores_approx = tq_per_head[h].attention_scores(q, quantized_keys[h]) * scale

    weights_exact = softmax(scores_exact)
    weights_approx = softmax(scores_approx)

    kl = float(np.sum(weights_exact * np.log(weights_exact / (weights_approx + 1e-30) + 1e-30)))
    l1 = float(np.sum(np.abs(weights_exact - weights_approx)))

    print(f"  Attention weight quality (head 0, softmax)")
    print(f"    KL divergence:  {kl:.6f}")
    print(f"    L1 distance:    {l1:.6f}\n")

    tag = "PASS" if all_match else "PARTIAL"
    print(f"  [{tag}] Top-{top_k} token agreement: "
          f"{'all heads match' if all_match else 'some heads differ'}\n")


if __name__ == "__main__":
    main()
