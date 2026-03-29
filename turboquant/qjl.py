"""QJL — Quantized Johnson-Lindenstrauss 1-bit quantizer.

Stores sign(H @ x) plus ||x||.  Provides an unbiased inner-product
estimator using the asymmetric formula:

    E[ sqrt(pi/2) * ||x|| * mean( (H @ y) * sign(H @ x) ) ] = <y, x>
"""

import numpy as np
from dataclasses import dataclass
from .utils import random_rotation_matrix


@dataclass
class QJLQuantized:
    """Quantized representation: 1 sign bit per coordinate + scalar norm."""
    sign_bits: np.ndarray   # int8, values in {-1, +1}, shape (d,)
    norm: float              # ||x||_2


class QJL:
    """1-bit quantizer with zero-overhead unbiased inner products.

    Parameters
    ----------
    dim : int
        Vector dimensionality.
    seed : int
        Reproducible seed for the projection matrix.
    """

    def __init__(self, dim: int, seed: int = 42):
        self.dim = dim
        self.seed = seed
        rng = np.random.default_rng(seed)
        self.H = random_rotation_matrix(dim, rng)

    # ------------------------------------------------------------------ #
    #  Core API                                                           #
    # ------------------------------------------------------------------ #

    def quantize(self, x: np.ndarray) -> QJLQuantized:
        """Compress *x* to 1 sign-bit per coordinate + scalar norm."""
        x = np.asarray(x, dtype=np.float64)
        norm = float(np.linalg.norm(x))
        z = self.H @ x
        sign_bits = np.sign(z).astype(np.int8)
        sign_bits[sign_bits == 0] = 1          # tie-break (measure-zero event)
        return QJLQuantized(sign_bits=sign_bits, norm=norm)

    def inner_product(self, query: np.ndarray, quantized: QJLQuantized) -> float:
        """Unbiased estimate of <query, x>.

        The query is projected at full precision (NOT quantised).
        """
        query = np.asarray(query, dtype=np.float64)
        z_q = self.H @ query                   # full precision
        return float(
            np.sqrt(np.pi / 2)
            * quantized.norm
            * np.mean(z_q * quantized.sign_bits)
        )

    def dequantize(self, quantized: QJLQuantized) -> np.ndarray:
        """Approximate reconstruction (unbiased in expectation)."""
        return (
            np.sqrt(np.pi / 2) / self.dim
            * quantized.norm
            * (self.H.T @ quantized.sign_bits.astype(np.float64))
        )
