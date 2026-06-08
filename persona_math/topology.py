"""
Topology — M16-M18
==================
M16  Betti numbers (persistent homology approximation)
M17  Fractal dimension (box-counting)
M18  Manifold dimension (PCA intrinsic)
"""
import numpy as np


def _to_100(P: np.ndarray) -> np.ndarray:
    """Pad/trim to exactly 100 elements for block-structure operations."""
    if len(P) == 100:
        return P
    out = np.zeros(100)
    m = min(len(P), 100)
    out[:m] = P[:m]
    return out


def betti_numbers(P: np.ndarray, threshold: float = 0.3) -> dict:
    """
    Approximate Betti numbers via Vietoris-Rips on 10 block means.
    Threshold controls edge formation between block nodes.
    """
    blocks = _to_100(P).reshape(10, 10).mean(axis=1)
    dist = np.abs(blocks[:, None] - blocks[None, :])
    adj = (dist < threshold).astype(int)
    np.fill_diagonal(adj, 0)

    # β0: connected components via union-find with path compression
    parent = list(range(10))
    find = lambda x: x if parent[x] == x else (parent.__setitem__(x, find(parent[x])) or find(parent[x]))  # noqa: E731

    for i in range(10):
        for j in range(i + 1, 10):
            if adj[i, j]:
                parent[find(i)] = find(j)

    beta0 = len({find(i) for i in range(10)})

    # β1: Euler characteristic for graph: β1 = edges - nodes + β0
    edges = int(adj.sum() // 2)
    beta1 = max(0, edges - 10 + beta0)

    # β2: voids approximated by triangles not bounding a filled face
    # count unfilled triangles as a proxy — non-obvious: exact β2 needs simplicial homology
    triangles = 0
    for i in range(10):
        for j in range(i + 1, 10):
            for k in range(j + 1, 10):
                if adj[i, j] and adj[j, k] and adj[i, k]:
                    triangles += 1
    beta2 = max(0, triangles - edges + beta0 - 1)

    return {"M16": True, "beta0": beta0, "beta1": beta1, "beta2": beta2}


def fractal_dimension(P: np.ndarray) -> dict:
    """
    Box-counting fractal dimension on the 100-dim signal.
    Slope computed via least-squares on log-log scale.
    """
    signal = P  # treat as 1D signal in [0, 1]
    log_eps, log_N = [], []
    for eps in [0.1, 0.2, 0.3, 0.4, 0.5]:
        n_bins = int(np.ceil(1.0 / eps))
        boxes = set()
        for i, v in enumerate(signal):
            pos_bin = int(i * n_bins / len(signal))
            amp_bin = int(np.clip(v, 0.0, 1.0 - 1e-9) / eps)
            boxes.add((pos_bin, amp_bin))
        N = max(len(boxes), 1)
        log_eps.append(np.log(eps))
        log_N.append(np.log(N))

    slope = np.polyfit(log_eps, log_N, 1)[0]
    d_f = round(float(-slope), 4)

    return {"M17": True, "fractal_dimension": d_f}


def manifold_dimension(P: np.ndarray) -> dict:
    """
    Intrinsic dimension via PCA on 10×10 block matrix (blocks × K-layers).
    Participation ratio avoids hard threshold sensitivity.
    """
    X = _to_100(P).reshape(10, 10)
    # center columns; rows are blocks, cols are layer-positions within block
    X_c = X - X.mean(axis=0)
    cov = X_c.T @ X_c / (X_c.shape[0] - 1)
    eigenvalues = np.linalg.eigvalsh(cov)
    eigenvalues = np.sort(eigenvalues)[::-1]
    eigenvalues = np.clip(eigenvalues, 0, None)  # numerical noise can yield tiny negatives

    total_var = eigenvalues.sum()
    cum_var = np.cumsum(eigenvalues) / (total_var + 1e-12)
    n_components = int(np.searchsorted(cum_var, 0.95)) + 1

    # participation ratio: effective number of active dimensions
    pr_num = (eigenvalues.sum()) ** 2
    pr_den = (eigenvalues ** 2).sum() + 1e-12
    participation_ratio = round(float(pr_num / pr_den), 4)

    return {
        "M18": True,
        "n_components_95pct": n_components,
        "participation_ratio": participation_ratio,
    }
