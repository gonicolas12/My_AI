"""Lloyd-Max codebook solver for the sphere marginal distribution.

After random orthogonal rotation, each coordinate of a unit-sphere vector
in R^d has marginal pdf:

    f(t) = Gamma(d/2) / (sqrt(pi) * Gamma((d-1)/2)) * (1 - t^2)^((d-3)/2)

on [-1, 1].  This is Beta((d-1)/2, (d-1)/2) rescaled from [0,1] to [-1,1].
"""

import numpy as np
from scipy import integrate, special
from scipy.stats import beta as beta_dist

# Module-level cache: (dim, bits) -> codebook array
_codebook_cache: dict[tuple[int, int], np.ndarray] = {}


def sphere_marginal_pdf(t: np.ndarray, d: int) -> np.ndarray:
    """PDF of a single coordinate of a uniform point on S^{d-1}."""
    t = np.asarray(t, dtype=np.float64)
    if d == 2:
        return np.where(np.abs(t) <= 1.0, 0.5, 0.0)
    log_norm = (
        special.gammaln(d / 2)
        - 0.5 * np.log(np.pi)
        - special.gammaln((d - 1) / 2)
    )
    exponent = (d - 3) / 2
    val = np.exp(log_norm) * np.power(np.maximum(1.0 - t ** 2, 0.0), exponent)
    return np.where(np.abs(t) <= 1.0, val, 0.0)


def _pdf_scalar(t: float, d: int) -> float:
    return float(sphere_marginal_pdf(np.array([t]), d)[0])


def lloyd_max(d: int, b: int, max_iter: int = 300, tol: float = 1e-13) -> np.ndarray:
    """Compute optimal 2^b-level Lloyd-Max codebook for the sphere marginal.

    Returns sorted array of 2^b centroids in [-1, 1].
    """
    n_centroids = 1 << b
    if n_centroids == 1:
        # Single centroid = mean of symmetric distribution = 0
        return np.array([0.0])

    # Initialise from quantiles of Beta((d-1)/2, (d-1)/2) mapped to [-1, 1]
    a_param = (d - 1) / 2
    quantiles = np.linspace(1 / (2 * n_centroids), 1 - 1 / (2 * n_centroids), n_centroids)
    centroids = beta_dist.ppf(quantiles, a_param, a_param) * 2 - 1

    pdf = lambda t: _pdf_scalar(t, d)

    for _ in range(max_iter):
        # Boundaries = midpoints between consecutive centroids
        boundaries = np.empty(n_centroids + 1)
        boundaries[0] = -1.0
        boundaries[-1] = 1.0
        boundaries[1:-1] = (centroids[:-1] + centroids[1:]) / 2

        new_centroids = np.empty_like(centroids)
        for i in range(n_centroids):
            lo, hi = boundaries[i], boundaries[i + 1]
            if hi - lo < 1e-15:
                new_centroids[i] = (lo + hi) / 2
                continue
            num, _ = integrate.quad(lambda t: t * pdf(t), lo, hi, limit=100)
            den, _ = integrate.quad(pdf, lo, hi, limit=100)
            new_centroids[i] = num / den if den > 1e-30 else (lo + hi) / 2

        if np.max(np.abs(new_centroids - centroids)) < tol:
            centroids = new_centroids
            break
        centroids = new_centroids

    return centroids


def get_codebook(d: int, b: int) -> np.ndarray:
    """Get (or compute and cache) the Lloyd-Max codebook for dimension *d* at *b* bits."""
    key = (d, b)
    if key not in _codebook_cache:
        _codebook_cache[key] = lloyd_max(d, b)
    return _codebook_cache[key]


def precompute_codebooks(d: int, bit_widths: tuple[int, ...] = (1, 2, 3, 4, 7, 8)) -> None:
    """Pre-warm the codebook cache for common bit-widths."""
    for b in bit_widths:
        get_codebook(d, b)
