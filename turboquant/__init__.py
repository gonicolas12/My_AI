"""TurboQuant — Extreme vector compression with unbiased inner products.

Implements the TurboQuant algorithm from Google Research (ICLR 2026).
Achieves >= 6x memory reduction at 3 bits/dim with zero precision loss
on inner-product estimation.

Quick start
-----------
>>> from turboquant import TurboQuantProd
>>> tq = TurboQuantProd(bits=3, dim=128, seed=42)
>>> q  = tq.quantize(key_vector)
>>> score = tq.inner_product(query, q)   # E[score] = <query, key>
>>> key_approx = tq.dequantize(q)
"""

from .turboquant_prod import TurboQuantProd, TurboQuantized
from .polar_quant import PolarQuant, PolarQuantized
from .qjl import QJL, QJLQuantized
from .codebook import get_codebook, lloyd_max, precompute_codebooks

__all__ = [
    "TurboQuantProd",
    "TurboQuantized",
    "PolarQuant",
    "PolarQuantized",
    "QJL",
    "QJLQuantized",
    "get_codebook",
    "lloyd_max",
    "precompute_codebooks",
]

__version__ = "0.1.0"
