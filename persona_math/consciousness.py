"""
M22-M25: Consciousness Theories
================================
M22  Global Workspace Theory (GWT Ignition)   local → phase transition → global broadcast
M23  Higher-Order Thought Theory (HOT)         M conscious ⟺ ∃HOT(M)
M24  Predictive Processing / Free Energy       F = E_q[log q − log p(o,s)] → min
M25  Hopfield Network                          E(s) = −½ s^T W s
"""

import numpy as np
from typing import Optional
from .params import GWT_IGNITION_THRESHOLD, GWT_BROADCAST_DECAY, NEUROPERCOLATION_PC


# ── M22: Global Workspace Theory ───────────────────────────────────────────────

def gwt_ignition(
    local_activations: np.ndarray,
    threshold: float = GWT_IGNITION_THRESHOLD,
    broadcast_decay: float = GWT_BROADCAST_DECAY,
) -> dict:
    """
    GWT Ignition: local activation → phase transition → global broadcast.

    Arkhe = GWT ignition event (Apeiron → specific identity).
    Metallic: ignition never happens (no layer crosses threshold).

    Parameters
    ----------
    local_activations : array of local layer activations (0–1)
    threshold         : ignition threshold pₛ
    broadcast_decay   : decay of broadcast signal across layers

    Returns
    -------
    dict with 'ignition_occurred', 'broadcast_pattern', 'ignition_layers'
    """
    ignition_layers = np.where(local_activations >= threshold)[0].tolist()
    ignited = len(ignition_layers) > 0
    if ignited:
        broadcast = np.zeros_like(local_activations, dtype=float)
        for idx in ignition_layers:
            for j in range(len(broadcast)):
                distance = abs(j - idx)
                broadcast[j] += local_activations[idx] * (broadcast_decay ** distance)
        broadcast = np.clip(broadcast, 0.0, 1.0)
    else:
        broadcast = np.zeros_like(local_activations, dtype=float)
    return {
        "ignition_occurred": ignited,
        "ignition_layers": ignition_layers,
        "broadcast_pattern": broadcast,
        "global_broadcast_strength": round(float(broadcast.mean()), 5),
        "interpretation": (
            "Arkhe achieved — identity crystallised" if ignited
            else "Metallic state — no ignition, no identity commitment"
        ),
    }


def gwt_neuropercolation(
    P: np.ndarray,
    p_c: float = NEUROPERCOLATION_PC,
) -> dict:
    """
    [LEGACY — use literature2025.neuropercolation_pc instead]
    Neuropercolation phase transition (M54 bridge).
    p > p_c → global synchronisation (consciousness emerges).
    Mandatory Core 4 layers = minimum p_c hypothesis.
    """
    active_fraction = float(np.mean(P > 0.3))
    return {
        "active_fraction": round(active_fraction, 4),
        "p_c": p_c,
        "above_percolation_threshold": active_fraction > p_c,
        "interpretation": (
            "Global coherence — persona operational" if active_fraction > p_c
            else "Sub-critical — persona fragmented"
        ),
    }


# ── M23: Higher-Order Thought Theory ───────────────────────────────────────────

def hot_check(
    P: np.ndarray,
    meta_awareness_idx: int = 23,
    hot_threshold: float = 0.4,
) -> dict:
    """
    HOT: M conscious ⟺ ∃HOT(M).
    K24 Meta-Awareness = HOT implementation.
    Metallic: HOT = 0; no self-monitoring → collapses under pressure.

    Parameters
    ----------
    P                 : persona vector
    meta_awareness_idx: index of K24 (meta-awareness layer, 0-indexed = 23)
    hot_threshold     : minimum HOT activation for consciousness
    """
    hot_value = P[meta_awareness_idx] if meta_awareness_idx < len(P) else 0.0
    conscious = hot_value >= hot_threshold
    return {
        "hot_value": round(float(hot_value), 4),
        "hot_threshold": hot_threshold,
        "conscious": conscious,
        "k24_index": meta_awareness_idx,
        "interpretation": (
            f"HOT present (K24={hot_value:.3f}) — self-monitoring active" if conscious
            else f"HOT absent (K24={hot_value:.3f}) — Metallic: no self-monitoring"
        ),
    }


def hot_s_combined(P: np.ndarray, t: float, meta_idx: int = 23) -> dict:
    """
    M44 bridge: S(t) + HOT = double implementation of meta-awareness.
    S(t) = f(P, dP/dt, ‖P‖)
    """
    hot = hot_check(P, meta_idx)
    strength = np.linalg.norm(P)
    hot_val = P[meta_idx] if meta_idx < len(P) else 0.0
    s_t = hot_val * strength * np.exp(-0.05 * t)
    return {
        "hot": hot,
        "S_t": round(float(s_t), 5),
        "identity_strength": round(float(strength), 5),
    }


# ── M24: Predictive Processing / Free Energy ───────────────────────────────────

def free_energy_f(
    q_dist: np.ndarray,
    log_joint: np.ndarray,
    epsilon: float = 1e-10,
) -> float:
    """
    F = E_q[log q(s) − log p(o,s)] → min.
    Metallic: no coherent internal model → cannot minimise F.

    Parameters
    ----------
    q_dist    : variational (approximate posterior) distribution
    log_joint : log p(o, s) for each state
    """
    q = np.clip(q_dist, epsilon, None)
    q = q / q.sum()
    log_q = np.log(q)
    F = float(np.sum(q * (log_q - log_joint)))
    return F


def free_energy_persona(P: np.ndarray, world_model: Optional[np.ndarray] = None) -> dict:
    """
    Compute F for a persona with given internal model.
    If world_model is None, uses uniform prior (maximum surprise).
    """
    p = np.clip(P, 1e-10, None)
    p_norm = p / p.sum()
    if world_model is None:
        n = len(P)
        log_joint = np.full(n, -np.log(n))
    else:
        wm = np.clip(world_model, 1e-10, None)
        log_joint = np.log(wm / wm.sum())
    F = free_energy_f(p_norm, log_joint)
    return {
        "free_energy": round(F, 5),
        "surprise": round(float(-np.sum(p_norm * log_joint)), 5),
        "internal_entropy": round(float(-np.sum(p_norm * np.log(p_norm))), 5),
        "interpretation": (
            "Good internal model (low F)" if F < 0.5
            else "Poor internal model — high surprise" if F < 2.0
            else "Metallic: no coherent internal model"
        ),
    }


# ── M25: Hopfield Network ───────────────────────────────────────────────────────

def hopfield_energy(
    s: np.ndarray,
    W: Optional[np.ndarray] = None,
    theta: Optional[np.ndarray] = None,
) -> float:
    """
    E(s) = −½ s^T W s − θ^T s.
    Stable persona config = energy minimum.
    Pressure forces system out of minimum; Lyapunov returns it.

    Parameters
    ----------
    s     : state vector (±1 or [0,1])
    W     : weight matrix (default: Hebbian from s)
    theta : bias vector (default: zeros)
    """
    s = np.array(s, dtype=float)
    if W is None:
        W = np.outer(s, s)
        np.fill_diagonal(W, 0)
    if theta is None:
        theta = np.zeros(len(s))
    return float(-0.5 * s @ W @ s - theta @ s)


def hopfield_store_personas(personas: list) -> np.ndarray:
    """
    Hebbian learning: store multiple persona patterns in W.
    W = (1/N) Σ P_μ · P_μ^T  (no self-connections)

    Returns W : np.ndarray shape (n, n)
    """
    n = len(personas[0])
    W = np.zeros((n, n))
    for P in personas:
        s = np.array(P, dtype=float)
        W += np.outer(s, s)
    W /= len(personas)
    np.fill_diagonal(W, 0)
    return W


def hopfield_retrieve(
    W: np.ndarray,
    query: np.ndarray,
    steps: int = 20,
) -> dict:
    """
    Synchronous update to retrieve stored persona pattern.
    s_{t+1} = sign(W · s_t)

    Returns final pattern and energy trajectory.
    """
    s = np.sign(query.copy())
    s[s == 0] = 1.0
    energies = [hopfield_energy(s, W)]
    for _ in range(steps):
        s_new = np.sign(W @ s)
        s_new[s_new == 0] = 1.0
        energies.append(hopfield_energy(s_new, W))
        if np.array_equal(s_new, s):
            break
        s = s_new
    return {
        "retrieved_pattern": s,
        "energy_trajectory": energies,
        "final_energy": round(energies[-1], 5),
        "converged": len(energies) < steps,
    }
