"""TurboQuantProd — unbiased inner-product quantiser at b bits/dim.

Two-step pipeline:
  Step 1: (b-1)-bit MSE quantisation via PolarQuant
  Step 2:  1-bit  QJL on the residual  (eliminates MSE bias)

Total budget: (b-1) + 1 = b  bits per coordinate.

Key property (Theorem 2 of the TurboQuant paper):
    E[ inner_product(y, quantize(x)) ] = <y, x>    (unbiased)
"""

import numpy as np
from dataclasses import dataclass
from .polar_quant import PolarQuant, PolarQuantized
from .qjl import QJL, QJLQuantized


@dataclass
class TurboQuantized:
    """Compact quantised state of a single vector."""
    mse_indices: np.ndarray     # uint8, shape (d,) — PolarQuant centroid indices
    qjl_signs: np.ndarray       # int8,  shape (d,) — QJL sign bits {-1, +1}
    norm: float                  # ||x||_2
    residual_norm: float         # ||x - x_mse||_2


class TurboQuantProd:
    """Unbiased inner-product quantiser combining PolarQuant + QJL.

    Parameters
    ----------
    bits : int   Total bit budget per coordinate (>= 2).
    dim  : int   Vector dimensionality.
    seed : int   Master seed (derives child seeds for PolarQuant and QJL).
    """

    def __init__(self, bits: int, dim: int, seed: int = 42):
        if bits < 2:
            raise ValueError(
                f"TurboQuantProd requires bits >= 2 (got {bits}). "
                "For 1-bit quantisation use QJL directly."
            )
        self.bits = bits
        self.dim = dim
        self.seed = seed

        rng = np.random.default_rng(seed)
        mse_seed = int(rng.integers(0, 2 ** 31))
        qjl_seed = int(rng.integers(0, 2 ** 31))

        self.mse = PolarQuant(bits=bits - 1, dim=dim, seed=mse_seed)
        self.qjl = QJL(dim=dim, seed=qjl_seed)

    # ------------------------------------------------------------------ #
    #  Core API                                                           #
    # ------------------------------------------------------------------ #

    def quantize(self, x: np.ndarray) -> TurboQuantized:
        """Quantise vector *x* (two-step: MSE + QJL on residual)."""
        x = np.asarray(x, dtype=np.float64)

        # Step 1 — MSE with (b-1) bits
        mse_q = self.mse.quantize(x)
        x_mse = self.mse.dequantize(mse_q)

        # Step 2 — QJL 1-bit on the residual
        residual = x - x_mse
        qjl_q = self.qjl.quantize(residual)

        return TurboQuantized(
            mse_indices=mse_q.indices,
            qjl_signs=qjl_q.sign_bits,
            norm=mse_q.norm,
            residual_norm=qjl_q.norm,
        )

    def inner_product(self, query: np.ndarray, quantized: TurboQuantized) -> float:
        """Unbiased inner-product estimate: E[result] = <query, x>."""
        query = np.asarray(query, dtype=np.float64)

        # MSE contribution: <query, x_mse>
        mse_q = PolarQuantized(indices=quantized.mse_indices, norm=quantized.norm)
        x_mse = self.mse.dequantize(mse_q)
        mse_contrib = np.dot(query, x_mse)

        # QJL contribution: unbiased estimate of <query, residual>
        qjl_q = QJLQuantized(sign_bits=quantized.qjl_signs, norm=quantized.residual_norm)
        qjl_contrib = self.qjl.inner_product(query, qjl_q)

        return float(mse_contrib + qjl_contrib)

    def dequantize(self, quantized: TurboQuantized) -> np.ndarray:
        """Approximate full-precision reconstruction."""
        mse_q = PolarQuantized(indices=quantized.mse_indices, norm=quantized.norm)
        x_mse = self.mse.dequantize(mse_q)

        r_hat = (
            np.sqrt(np.pi / 2) / self.dim
            * quantized.residual_norm
            * (self.qjl.H.T @ quantized.qjl_signs.astype(np.float64))
        )
        return x_mse + r_hat

    # ------------------------------------------------------------------ #
    #  Batch / attention helpers                                          #
    # ------------------------------------------------------------------ #

    def attention_scores(
        self, query: np.ndarray, quantized_keys: list[TurboQuantized]
    ) -> np.ndarray:
        """Compute <query, k_i> for many quantised keys efficiently.

        Precomputes the rotated query vectors once (O(d^2)),
        then O(d) per key instead of O(d^2).
        """
        query = np.asarray(query, dtype=np.float64)

        # Precompute: rotate query into both coordinate systems
        Pi_q = self.mse.Pi @ query        # for MSE inner products
        H_q = self.qjl.H @ query          # for QJL inner products
        sqrt_pi_2 = np.sqrt(np.pi / 2)
        codebook = self.mse.codebook

        scores = np.empty(len(quantized_keys), dtype=np.float64)
        for i, qk in enumerate(quantized_keys):
            # MSE in rotated space: <Pi @ query, codebook[indices]> * norm
            x_rot_hat = codebook[qk.mse_indices]
            mse_part = qk.norm * np.dot(Pi_q, x_rot_hat)

            # QJL: sqrt(pi/2) * r_norm * mean(H_q * signs)
            qjl_part = sqrt_pi_2 * qk.residual_norm * np.mean(
                H_q * qk.qjl_signs
            )

            scores[i] = mse_part + qjl_part
        return scores

    # ------------------------------------------------------------------ #
    #  Storage analysis                                                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def storage_bits(dim: int, bits: int) -> int:
        """Theoretical bit-packed storage per vector (excluding object overhead)."""
        # (b-1)*d bits for MSE indices  +  d bits for QJL signs
        # + 64 bits for two float32 scalars (norm, residual_norm)
        return bits * dim + 64

    @staticmethod
    def float32_bits(dim: int) -> int:
        return dim * 32
