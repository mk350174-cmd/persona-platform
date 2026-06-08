"""Tensor & Spectral — M33-M36 decomposition, Fiedler, FFT, adjoint tools."""

import numpy as np


def persona_tensor(P):
    """M33: Tensor decomposition of P (100-dim) via SVD on 10×10 reshape."""
    P = np.array(P, dtype=float)
    M = P.reshape(10, 10)
    U, sv, Vt = np.linalg.svd(M)
    max_sv = sv[0] if sv[0] != 0 else 1.0
    rank_approx = int(np.sum(sv > 0.1 * max_sv))
    total_var = np.sum(sv ** 2)
    explained = np.sum(sv[:3] ** 2) / total_var if total_var > 0 else 0.0
    return {
        "singular_values": sv[:5].tolist(),
        "rank_approx": rank_approx,
        "explained_variance_ratio": float(explained),
        "frobenius_norm": float(np.linalg.norm(M, "fro")),
    }


def fiedler_spectral(W):
    """M34: Fiedler value from W (10×10 matrix or 100-dim vector → block corr)."""
    W = np.array(W, dtype=float)
    if W.ndim == 1 and W.shape[0] == 100:
        M = W.reshape(10, 10)
        # Build symmetric block correlation matrix
        W = (M @ M.T) / 10.0
        np.fill_diagonal(W, 0.0)
        W = np.abs(W)
    W = W.reshape(10, 10)
    W = (W + W.T) / 2.0          # ensure symmetry
    np.fill_diagonal(W, 0.0)     # no self-loops
    D = np.diag(W.sum(axis=1))
    L = D - W
    eigenvalues = np.linalg.eigh(L)[0]
    eigenvalues_sorted = np.sort(eigenvalues)
    lambda2 = float(eigenvalues_sorted[1])
    if lambda2 < 1e-8:
        interpretation = "disconnected"
    elif lambda2 < 0.5:
        interpretation = "poorly_connected"
    else:
        interpretation = "well_connected"
    return {
        "lambda2": lambda2,
        "algebraic_connectivity": lambda2,
        "interpretation": interpretation,
    }


def fourier_persona(P):
    """M35: Discrete Fourier transform of P (100-dim vector)."""
    P = np.array(P, dtype=float)
    spectrum = np.fft.fft(P)
    magnitudes = np.abs(spectrum)
    dominant_frequencies = np.argsort(magnitudes)[::-1][:5].tolist()
    # Spectral entropy (normalized over non-zero power)
    power = magnitudes ** 2
    total_power = power.sum()
    if total_power > 0:
        p_norm = power / total_power
        p_norm = p_norm[p_norm > 0]
        raw_entropy = -np.sum(p_norm * np.log(p_norm))
        spectral_entropy = float(raw_entropy / np.log(len(P)))
    else:
        spectral_entropy = 0.0
    low_freq_power = float(power[:10].sum())
    high_freq_power = float(power[-10:].sum())
    periodicity_index = float(low_freq_power / high_freq_power) if high_freq_power > 0 else float("inf")
    return {
        "dominant_frequencies": dominant_frequencies,
        "spectral_entropy": spectral_entropy,
        "low_freq_power": low_freq_power,
        "high_freq_power": high_freq_power,
        "periodicity_index": periodicity_index,
    }


def adjoint_transform(P, operator=None):
    """M36: Adjoint operator A†. Compute ⟨P, A†P⟩ = ⟨AP, P⟩ inner product."""
    P = np.array(P, dtype=float)
    n = len(P)
    if operator is None:
        # Block-diagonal identity (10×10 blocks on 100-dim vector)
        A = np.eye(n)
    else:
        A = np.array(operator, dtype=float)
        if A.ndim == 1:
            A = np.diag(A)
    # Adjoint of real matrix is its transpose
    A_adj = A.T
    AP = A @ P
    A_adj_P = A_adj @ P
    inner_product = float(P @ A_adj_P)        # ⟨P, A†P⟩
    inner_AP_P = float(AP @ P)                # ⟨AP, P⟩
    adjoint_check = bool(abs(inner_product - inner_AP_P) < 1e-6)
    # Hermitian deviation: ‖A - A†‖_F
    hermitian_deviation = float(np.linalg.norm(A - A_adj, "fro"))
    return {
        "inner_product": inner_product,
        "adjoint_check": adjoint_check,
        "hermitian_deviation": hermitian_deviation,
    }
