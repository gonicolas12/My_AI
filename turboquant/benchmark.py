"""TurboQuant validation benchmark.

Run:  python -m turboquant.benchmark
"""

import sys
import os
import time
import numpy as np

# Allow running as standalone script
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from turboquant import TurboQuantProd, PolarQuant  # pylint: disable=wrong-import-position


def banner(title: str) -> None:
    """Print a section banner."""
    print(f"\n{'=' * 56}")
    print(f"  {title}")
    print(f"{'=' * 56}\n")


# ---------------------------------------------------------------------- #
#  1. Unbiasedness test                                                   #
# ---------------------------------------------------------------------- #
def test_unbiasedness(dim: int = 128, bits: int = 3, n_samples: int = 1000, seed: int = 0):
    """Verify the inner-product estimator is unbiased across many samples."""
    print("1. UNBIASEDNESS TEST")
    print(f"   dim={dim}  bits={bits}  samples={n_samples}\n")

    tq = TurboQuantProd(bits=bits, dim=dim, seed=42)
    rng = np.random.default_rng(seed)

    biases = np.empty(n_samples)
    for i in range(n_samples):
        x = rng.standard_normal(dim)
        y = rng.standard_normal(dim)
        exact = float(np.dot(y, x))
        q = tq.quantize(x)
        approx = tq.inner_product(y, q)
        biases[i] = approx - exact

    mean_bias = np.mean(biases)
    std_bias = np.std(biases)
    max_abs = np.max(np.abs(biases))
    rel_bias = np.abs(mean_bias) / (std_bias / np.sqrt(n_samples) + 1e-30)

    print(f"   Mean bias:           {mean_bias:+.6f}  (ideal: 0)")
    print(f"   Std of error:        {std_bias:.6f}")
    print(f"   Max |error|:         {max_abs:.4f}")
    print(f"   |mean|/SE:           {rel_bias:.2f}  (< 3 => consistent with zero)")
    ok = rel_bias < 3.0
    tag = "PASS" if ok else "FAIL"
    print(f"   [{tag}] Unbiased estimator {'confirmed' if ok else 'NOT confirmed'}\n")
    return ok


# ---------------------------------------------------------------------- #
#  2. Compression ratio                                                   #
# ---------------------------------------------------------------------- #
def test_compression(dim: int = 128):
    """Report compression ratios for each supported bit-width."""
    print("2. COMPRESSION RATIO")
    fp32_bytes = dim * 4
    print(f"   dim={dim}   float32 baseline = {fp32_bytes} bytes\n")
    print(f"   {'Bits':>4}  {'Float32':>9}  {'TurboQuant':>11}  {'Ratio':>7}")
    print(f"   {'----':>4}  {'---------':>9}  {'-----------':>11}  {'-----':>7}")

    all_ok = True
    for b in [2, 3, 4, 8]:
        tq_bits = TurboQuantProd.storage_bits(dim, b)
        tq_bytes = tq_bits / 8
        ratio = fp32_bytes / tq_bytes
        print(f"   {b:4d}  {fp32_bytes:7d} B  {tq_bytes:9.0f} B  {ratio:6.1f}x")
        if b <= 3 and ratio < 6.0:
            all_ok = False

    tag = "PASS" if all_ok else "FAIL"
    print(f"\n   [{tag}] All ratios >= 6x for <= 3 bits\n")
    return all_ok


# ---------------------------------------------------------------------- #
#  3. MSE by bit-width                                                    #
# ---------------------------------------------------------------------- #
def test_mse(dim: int = 128, n_samples: int = 500, seed: int = 1):
    """Measure reconstruction MSE for PolarQuant across bit-widths."""
    print("3. MSE BY BIT-WIDTH (PolarQuant / TurboQuantMSE)")
    print(f"   dim={dim}  samples={n_samples}\n")
    rng = np.random.default_rng(seed)

    print(f"   {'Bits':>4}  {'MSE':>12}  {'Normalised MSE':>15}  {'Theoretical UB':>15}")
    print(f"   {'----':>4}  {'---':>12}  {'--------------':>15}  {'--------------':>15}")

    for b in [1, 2, 3, 4, 8]:
        pq = PolarQuant(bits=b, dim=dim, seed=42)
        mse_acc = 0.0
        for _ in range(n_samples):
            x = rng.standard_normal(dim)
            q = pq.quantize(x)
            x_hat = pq.dequantize(q)
            mse_acc += float(np.sum((x - x_hat) ** 2))
        mse = mse_acc / n_samples
        norm_mse = mse / dim   # per-coordinate MSE normalised by E[||x||^2] = dim
        # Theoretical upper bound: sqrt(3)*pi/2 * (1/4^b) per coordinate
        ub = np.sqrt(3) * np.pi / 2 * (1.0 / 4 ** b)
        print(f"   {b:4d}  {mse:12.6f}  {norm_mse:15.6f}  {ub:15.6f}")

    print()


# ---------------------------------------------------------------------- #
#  4. Speed benchmark                                                     #
# ---------------------------------------------------------------------- #
def test_speed(dim: int = 128, n_vectors: int = 10_000, bits: int = 3, seed: int = 2):
    """Benchmark quantisation and inner-product throughput."""
    print("4. SPEED BENCHMARK")
    print(f"   dim={dim}  vectors={n_vectors}  bits={bits}\n")

    tq = TurboQuantProd(bits=bits, dim=dim, seed=42)
    rng = np.random.default_rng(seed)

    vectors = rng.standard_normal((n_vectors, dim))
    query = rng.standard_normal(dim)

    # Quantize
    t0 = time.perf_counter()
    quantized = [tq.quantize(v) for v in vectors]
    t_quant = time.perf_counter() - t0

    # Inner products (single-vector API)
    t0 = time.perf_counter()
    _ = [tq.inner_product(query, q) for q in quantized]
    t_ip_single = time.perf_counter() - t0

    # Inner products (batch API with precomputed rotations)
    t0 = time.perf_counter()
    scores_batch = tq.attention_scores(query, quantized)
    t_ip_batch = time.perf_counter() - t0

    # Naive float32 dot products
    t0 = time.perf_counter()
    scores_exact = vectors @ query
    t_ip_fp32 = time.perf_counter() - t0

    # Accuracy of batch vs exact
    corr = np.corrcoef(scores_batch, scores_exact)[0, 1]

    print(f"   Quantize {n_vectors} vectors:       {t_quant:.3f}s  ({t_quant/n_vectors*1e6:.1f} us/vec)")
    print(f"   Inner product (single):      {t_ip_single:.3f}s  ({t_ip_single/n_vectors*1e6:.1f} us/pair)")
    print(f"   Inner product (batch):       {t_ip_batch:.3f}s  ({t_ip_batch/n_vectors*1e6:.1f} us/pair)")
    print(f"   Float32 dot product:         {t_ip_fp32:.4f}s  ({t_ip_fp32/n_vectors*1e6:.1f} us/pair)")
    print(f"   Pearson correlation:         {corr:.6f}")
    print(f"   Batch speedup vs single:     {t_ip_single/t_ip_batch:.1f}x")
    print()


# ---------------------------------------------------------------------- #
#  5. TurboQuantProd end-to-end MSE                                       #
# ---------------------------------------------------------------------- #
def test_turboquant_mse(dim: int = 128, n_samples: int = 500, seed: int = 3):
    """Measure end-to-end reconstruction MSE for TurboQuantProd."""
    print("5. TURBOQUANTPROD RECONSTRUCTION MSE")
    print(f"   dim={dim}  samples={n_samples}\n")
    rng = np.random.default_rng(seed)

    print(f"   {'Bits':>4}  {'MSE':>12}  {'Normalised':>12}")
    print(f"   {'----':>4}  {'---':>12}  {'----------':>12}")

    for b in [2, 3, 4, 8]:
        tq = TurboQuantProd(bits=b, dim=dim, seed=42)
        mse_acc = 0.0
        for _ in range(n_samples):
            x = rng.standard_normal(dim)
            q = tq.quantize(x)
            x_hat = tq.dequantize(q)
            mse_acc += float(np.sum((x - x_hat) ** 2))
        mse = mse_acc / n_samples
        print(f"   {b:4d}  {mse:12.6f}  {mse / dim:12.6f}")

    print()


# ---------------------------------------------------------------------- #
#  Main                                                                   #
# ---------------------------------------------------------------------- #
def main():
    """Run all validation benchmarks and print a summary."""
    banner("TurboQuant Validation Benchmark")

    ok1 = test_unbiasedness()
    ok2 = test_compression()
    test_mse()
    test_speed()
    test_turboquant_mse()

    banner("Summary")
    status = "ALL PASSED" if (ok1 and ok2) else "SOME TESTS FAILED"
    print(f"  {status}")
    print()


if __name__ == "__main__":
    main()
