"""Utility functions: Hadamard matrices, random rotations, helpers."""

import numpy as np


def is_power_of_2(n: int) -> bool:
    """Return True if n is a strictly positive power of 2."""
    return n > 0 and (n & (n - 1)) == 0


def hadamard_matrix(d: int) -> np.ndarray:
    """Sylvester construction of d x d Hadamard matrix (d must be power of 2).

    H^T H = d * I_d
    """
    if not is_power_of_2(d):
        raise ValueError(f"d must be a power of 2, got {d}")
    hadamard = np.array([[1.0]])
    while hadamard.shape[0] < d:
        hadamard = np.block([[hadamard, hadamard], [hadamard, -hadamard]])
    return hadamard


def signed_hadamard_matrix(d: int, rng: np.random.Generator) -> np.ndarray:
    """Randomised orthogonal matrix: (1/sqrt(d)) * H @ diag(signs).

    Properties:
      - Orthogonal: Pi^T Pi = I_d
      - O(d log d) fast multiply via Walsh-Hadamard transform
      - Approximate JL property for large d
    """
    hadamard = hadamard_matrix(d)
    signs = rng.choice([-1.0, 1.0], size=d)
    return (hadamard * signs[np.newaxis, :]) / np.sqrt(d)


def random_orthogonal_matrix(d: int, rng: np.random.Generator) -> np.ndarray:
    """Haar-distributed random orthogonal matrix via QR of Gaussian."""
    g_mat = rng.standard_normal((d, d))
    q_mat, r_mat = np.linalg.qr(g_mat)
    # Correct signs so q_mat is truly Haar-distributed
    q_mat = q_mat @ np.diag(np.sign(np.diag(r_mat)))
    return q_mat


def random_rotation_matrix(d: int, rng: np.random.Generator) -> np.ndarray:
    """Signed Hadamard if d is power of 2, else Haar random orthogonal."""
    if is_power_of_2(d):
        return signed_hadamard_matrix(d, rng)
    return random_orthogonal_matrix(d, rng)


def fast_hadamard_transform(x: np.ndarray, signs: np.ndarray | None = None) -> np.ndarray:
    """Vectorised O(d log d) Walsh-Hadamard transform (unnormalised).

    Returns H @ diag(signs) @ x / sqrt(d)  when signs is provided,
    or      H @ x / sqrt(d)                otherwise.
    """
    y = x.astype(np.float64, copy=True)
    if signs is not None:
        y = y * signs
    n = len(y)
    h = 1
    while h < n:
        y = y.reshape(-1, 2 * h)
        left = y[:, :h].copy()
        right = y[:, h:].copy()
        y[:, :h] = left + right
        y[:, h:] = left - right
        y = y.reshape(-1)
        h *= 2
    return y / np.sqrt(n)
