"""PolarQuant / TurboQuantMSE — MSE-optimal per-coordinate scalar quantizer.

Workflow:
  1. Normalise x to the unit sphere.
  2. Apply a fixed random orthogonal rotation Pi.
  3. Quantise each rotated coordinate independently with a Lloyd-Max
     codebook tuned to the sphere-marginal distribution.

The rotation makes coordinates approximately i.i.d. with a known
distribution (Beta((d-1)/2, (d-1)/2) on [-1,1]), enabling a single
shared codebook for all coordinates.
"""

import numpy as np
from dataclasses import dataclass
from .utils import random_rotation_matrix
from .codebook import get_codebook


@dataclass
class PolarQuantized:
    """Quantized state: centroid indices + original L2 norm."""
    indices: np.ndarray   # uint8 (b <= 8) or uint16, shape (d,)
    norm: float            # ||x||_2


class PolarQuant:
    """TurboQuantMSE: per-coordinate scalar quantiser with random rotation.

    Parameters
    ----------
    bits : int   Number of bits per coordinate (1–8).
    dim  : int   Vector dimensionality.
    seed : int   Reproducible seed for the rotation matrix Pi.
    """

    def __init__(self, bits: int, dim: int, seed: int = 42):
        if bits < 1:
            raise ValueError(f"bits must be >= 1, got {bits}")
        self.bits = bits
        self.dim = dim
        self.seed = seed

        rng = np.random.default_rng(seed)
        self.Pi = random_rotation_matrix(dim, rng)

        self.codebook = get_codebook(dim, bits)            # shape (2^b,)
        # Decision boundaries = midpoints between consecutive centroids
        self.boundaries = (self.codebook[:-1] + self.codebook[1:]) / 2

    # ------------------------------------------------------------------ #
    #  Core API                                                           #
    # ------------------------------------------------------------------ #

    def quantize(self, x: np.ndarray) -> PolarQuantized:
        """Quantise *x* to centroid indices + norm."""
        x = np.asarray(x, dtype=np.float64)
        norm = float(np.linalg.norm(x))
        if norm < 1e-30:
            return PolarQuantized(
                indices=np.zeros(self.dim, dtype=np.uint8),
                norm=0.0,
            )
        x_n = x / norm                              # unit sphere
        x_rot = self.Pi @ x_n                        # rotate
        indices = np.searchsorted(self.boundaries, x_rot).astype(np.uint8)
        return PolarQuantized(indices=indices, norm=norm)

    def dequantize(self, quantized: PolarQuantized) -> np.ndarray:
        """Reconstruct from centroid indices + norm."""
        x_rot_hat = self.codebook[quantized.indices]  # (d,)
        x_n_hat = self.Pi.T @ x_rot_hat               # inverse rotation
        return x_n_hat * quantized.norm
