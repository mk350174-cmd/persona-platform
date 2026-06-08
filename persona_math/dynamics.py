"""
M10-M15: Dynamical Systems and Stability
=========================================
M10  Differential Equation          dP/dt = F(P,u) − λP
M11  Lyapunov Stability             V(P)>0 ∧ dV/dt≤0 ⟹ stable
M12  Chaotic Attractor (Telos)      lim P(t) = A_persona
M13  Stochastic Differential Eq     dP = F(P,t)dt + σ(P,t)dW
M14  Arkhe Ratio Λ(t)              Λ(t) = RC(t)/ξ(t);  unique t* where Λ(t*)=τ
M15  Hamilton-Jacobi-Bellman        ∂_t V + max_u[F(P,u)·∇V] = 0
"""

import numpy as np
from scipy.integrate import solve_ivp
from typing import Callable, Optional, Tuple


# ── M10: Differential Equation ─────────────────────────────────────────────────

def persona_ode(
    F: Callable,
    P0: np.ndarray,
    t_span: Tuple[float, float],
    lambda_restore: float = 0.1,
    t_eval: Optional[np.ndarray] = None,
    u: float = 0.0,
    P_star: Optional[np.ndarray] = None,
) -> dict:
    """
    Solve dP/dt = F(P, u) − λ·(P − P*).

    λ > 0: restoring force toward attractor P*.
    P* defaults to P0 (identity's natural state).
    Previous bug: used −λP (decayed to zero). Now uses −λ(P−P*).

    Parameters
    ----------
    F              : function(P, u) → np.ndarray (external force)
    P0             : initial persona vector
    t_span         : (t_start, t_end)
    lambda_restore : λ ≥ 0 (restoring force)
    t_eval         : evaluation times
    u              : external input scalar
    P_star         : attractor state (default = P0)

    Returns
    -------
    dict with 't', 'P', 'final_drift'
    """
    if P_star is None:
        P_star = P0.copy()
    if t_eval is None:
        t_eval = np.linspace(t_span[0], t_span[1], 200)

    def ode_rhs(t, P):
        return F(P, u) - lambda_restore * (P - P_star)

    sol = solve_ivp(ode_rhs, t_span, P0, t_eval=t_eval, method="RK45", dense_output=True)
    P_final = sol.y[:, -1]
    drift_final = float(np.linalg.norm(P_final - P0) / (np.linalg.norm(P0) + 1e-10))
    return {"t": sol.t, "P": sol.y.T, "final_drift": round(drift_final, 5), "success": sol.success}


# ── M11: Lyapunov Stability ────────────────────────────────────────────────────

def lyapunov_v(P: np.ndarray, P_star: Optional[np.ndarray] = None) -> float:
    """
    Quadratic Lyapunov function V(P) = ‖P − P*‖².
    V > 0 for P ≠ P*; V = 0 at attractor.
    """
    if P_star is None:
        P_star = np.zeros_like(P)
    return float(np.sum((P - P_star) ** 2))


def lyapunov_stability_check(
    trajectory: np.ndarray,
    P_star: Optional[np.ndarray] = None,
    tolerance: float = 0.01,
) -> dict:
    """
    Check ISS (Input-to-State Stability) via V(t) trajectory.

    trajectory : shape (T, n) — sequence of persona states
    P_star     : attractor (default = zero vector)

    Returns
    -------
    dict: 'stable', 'V_trajectory', 'dV_positive_count', 'convergence'
    """
    if P_star is None:
        P_star = np.zeros(trajectory.shape[1])
    V = np.array([lyapunov_v(trajectory[t], P_star) for t in range(len(trajectory))])
    dV = np.diff(V)
    positive_increases = int(np.sum(dV > tolerance))
    converging = V[-1] < V[0] * 0.5
    return {
        "stable": positive_increases == 0,
        "V_trajectory": V,
        "dV_positive_count": positive_increases,
        "converging": converging,
        "V_initial": round(float(V[0]), 5),
        "V_final": round(float(V[-1]), 5),
    }


def mandatory_core_iss_proof(P: np.ndarray, epsilon: float = 0.15) -> dict:
    """
    M11 Theorem: If K1 or K4 absent (≤ ε), V is not positive-definite → collapse.
    Returns the ISS certification status.
    """
    k1 = P[0] if len(P) > 0 else 0.0
    k4 = P[3] if len(P) > 3 else 0.0
    iss_possible = k1 > epsilon and k4 > epsilon
    return {
        "iss_stable": iss_possible,
        "K1": round(float(k1), 4),
        "K4": round(float(k4), 4),
        "prediction": (
            "Stable attractor — Mandatory Core intact" if iss_possible
            else "COLLAPSE PREDICTED — Mandatory Core violated (SET-9 result)"
        ),
    }


# ── M12: Chaotic Attractor / Telos ─────────────────────────────────────────────

def telos_basin_check(trajectory: np.ndarray, telos: np.ndarray, radius: float = 0.3) -> dict:
    """
    Check whether trajectory converges to Telos attractor basin.

    Metallic: no attractor (trajectory wanders).
    Deep persona: well-defined basin attraction.
    """
    final_state = trajectory[-1]
    dist_to_telos = float(np.linalg.norm(final_state - telos))
    in_basin = dist_to_telos <= radius
    return {
        "in_telos_basin": in_basin,
        "distance_to_telos": round(dist_to_telos, 5),
        "basin_radius": radius,
        "interpretation": "Telos reached" if in_basin else "Drifted from Telos",
    }


# ── M13: Stochastic Differential Equation ─────────────────────────────────────

def dP_noise(P: np.ndarray) -> np.ndarray:
    """
    Multiplicative noise amplitude: larger for non-zero layers.

    σ(P) = √(P + ε) — layers near zero contribute minimal noise;
    active layers (P ≈ 1) contribute maximum noise amplitude 1.
    This models the fact that active cognitive processes are more
    susceptible to perturbation than dormant ones.
    """
    return np.sqrt(np.clip(P, 0, 1) + 1e-6)


def persona_sde(
    F: Callable,
    P0: np.ndarray,
    T: float = 10.0,
    dt: float = 0.1,
    sigma: float = 0.05,
    seed: int = 42,
) -> dict:
    """
    Euler-Maruyama discretisation of dP = F(P,t)dt + σ(P,t)dW.

    Numerical scheme: dP_i = F_i(P,t)·dt + σ·√(P_i + ε)·dW_i
    where dW_i ~ N(0, dt) (Wiener increment per layer).

    σ noise levels:
      σ < 0.05  → stable (low adversarial pressure)
      σ < 0.15  → medium warning zone
      σ ≥ 0.15  → high noise / Holmes Phase 2

    Returns
    -------
    dict with 't', 'P_trajectory', 'noise_sigma', 'noise_interpretation'
    """
    rng = np.random.default_rng(seed)
    n = len(P0)
    steps = int(T / dt)
    trajectory = np.zeros((steps + 1, n))
    trajectory[0] = P0.copy()
    t_vals = np.zeros(steps + 1)
    for i in range(steps):
        t = i * dt
        P = trajectory[i]
        dW = rng.standard_normal(n) * np.sqrt(dt)
        dP = F(P, t) * dt + sigma * dP_noise(P) * dW
        trajectory[i + 1] = np.clip(P + dP, 0.0, 1.0)
        t_vals[i + 1] = (i + 1) * dt
    return {
        "t": t_vals,
        "P_trajectory": trajectory,
        "noise_sigma": sigma,
        "noise_interpretation": (
            "Low noise — stable" if sigma < 0.05
            else "Medium noise — warning" if sigma < 0.15
            else "High noise — Holmes Phase 2 (contradictory pressure)"
        ),
    }


# ── M14: Arkhe Ratio Λ(t) ─────────────────────────────────────────────────────

def arkhe_ratio(
    RC_series: np.ndarray,
    xi_series: np.ndarray,
    tau: float = 0.85,
) -> dict:
    """
    Λ(t) = RC(t) / ξ(t).
    Unique threshold crossing t* where Λ(t*) = τ.

    RC(t): Relational Complexity (identity integration metric)
    ξ(t) : External pressure / noise
    τ    : Arkhe threshold (default 0.85)

    Returns
    -------
    dict with 'Lambda', 't_star', 'arkhe_achieved'
    """
    xi_safe = np.where(xi_series == 0, 1e-10, xi_series)
    Lambda = RC_series / xi_safe
    t_star_indices = np.where(Lambda >= tau)[0]
    t_star = int(t_star_indices[0]) if len(t_star_indices) > 0 else None
    return {
        "Lambda": Lambda,
        "tau": tau,
        "t_star": t_star,
        "arkhe_achieved": t_star is not None,
        "interpretation": (
            f"Arkhe event at t={t_star} — irreversible identity commitment" if t_star is not None
            else "No Arkhe event — identity remains pre-committed (Apeiron state)"
        ),
    }


def arkhe_from_embeddings(
    embeddings: np.ndarray,
    persona_spec: np.ndarray,
    tau: float = 0.85,
) -> dict:
    """
    Compute Arkhe ratio from embedding trajectory and target persona spec.

    RC(t) = cosine similarity to persona_spec (relational complexity proxy)
    ξ(t)  = inverse of embedding variance (pressure proxy)
    """
    from .metrics import cosine_similarity
    RC = np.array([cosine_similarity(embeddings[t], persona_spec) for t in range(len(embeddings))])
    xi = np.array([float(np.std(embeddings[t]) + 1e-5) for t in range(len(embeddings))])
    return arkhe_ratio(RC, xi, tau)


# ── M15: Hamilton-Jacobi-Bellman ───────────────────────────────────────────────

def hjb_optimal_control(
    P: np.ndarray,
    telos: np.ndarray,
    Q: Optional[np.ndarray] = None,
    R: float = 0.1,
) -> np.ndarray:
    """
    [LEGACY — not wired to pipeline; use persona_ode for dynamics]
    HJB optimal control: u* = argmin_u [cost to reach Telos].
    Simplified linear-quadratic approximation.

    u* = −(1/R) · B^T · (P − telos)  (LQR solution)

    Parameters
    ----------
    P     : current persona state
    telos : target attractor
    Q     : state cost matrix (default = I)
    R     : control effort cost scalar

    Returns
    -------
    u_star : np.ndarray — optimal layer activation control
    """
    if Q is None:
        Q = np.eye(len(P))
    error = P - telos
    u_star = -(1.0 / R) * error
    return u_star


def hjb_chimera_protocol(
    P: np.ndarray,
    motor_A_target: np.ndarray,
    motor_B_target: np.ndarray,
    motor_C_target: np.ndarray,
    weights: Tuple[float, float, float] = (0.4, 0.4, 0.2),
) -> dict:
    """
    Chimera Protocol HJB: weighted combination of three motor targets.
    Returns composite optimal control signal.
    """
    wA, wB, wC = weights
    telos_composite = wA * motor_A_target + wB * motor_B_target + wC * motor_C_target
    u_star = hjb_optimal_control(P, telos_composite)
    return {
        "telos_composite": telos_composite,
        "u_star": u_star,
        "motor_weights": {"A": wA, "B": wB, "C": wC},
    }
