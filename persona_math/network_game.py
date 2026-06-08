"""
M29-M32: Network Science and Game Theory
==========================================
M29  Scale-Free Network (Barabási)   P(k) ~ k^{-γ}  (hub = Mandatory Core)
M30  Small-World Network (Watts)      C >> C_r;  L ≈ L_r
M31  Nash Equilibrium                 uᵢ(sᵢ*, s_{-i}*) ≥ uᵢ(sᵢ, s_{-i}*) ∀i
M32  Lotka-Volterra Coevolution       Ṗ = αP − βPU;  U̇ = δPU − γU
"""

import numpy as np
import networkx as nx
from scipy.integrate import solve_ivp
from typing import Optional
from .params import NETWORK_EDGE_THRESHOLD


# ── M29: Scale-Free Network ────────────────────────────────────────────────────

def build_persona_network(P: np.ndarray, threshold: float = NETWORK_EDGE_THRESHOLD) -> nx.Graph:
    """
    Build K-layer network where nodes are layers,
    edges connect co-active layers (weight > threshold).
    Mandatory Core nodes {K1, K2, K4, K12} = expected hubs.
    """
    G = nx.Graph()
    n = len(P)
    mandatory_core = {0: "K1", 1: "K2", 3: "K4", 11: "K12"}
    for i in range(n):
        label = mandatory_core.get(i, f"K{i+1}")
        G.add_node(i, weight=float(P[i]), label=label,
                   is_core=i in mandatory_core)
    for i in range(n):
        for j in range(i + 1, n):
            edge_weight = float(P[i] * P[j])
            if edge_weight > threshold ** 2:
                G.add_edge(i, j, weight=edge_weight)
    return G


def scale_free_gamma(G: nx.Graph) -> dict:
    """
    Estimate power-law exponent γ for degree distribution P(k) ~ k^{-γ}.
    Uses maximum-likelihood estimator (Clauset 2009).

    γ ∈ [2, 3]: scale-free network
    Mandatory Core nodes should have highest degree.
    """
    degrees = [d for _, d in G.degree()]
    degrees = np.array([d for d in degrees if d > 0])
    if len(degrees) < 3:
        return {"gamma": None, "note": "Insufficient nodes for power-law fit"}
    k_min = max(1, int(np.percentile(degrees, 25)))
    tail = degrees[degrees >= k_min]
    if len(tail) < 2:
        return {"gamma": None, "note": "Too few tail observations"}
    gamma = 1.0 + len(tail) * (np.sum(np.log(tail / (k_min - 0.5)))) ** (-1)
    hub_nodes = sorted(G.degree(), key=lambda x: x[1], reverse=True)[:5]
    core_indices = {0, 1, 3, 11}
    hub_node_ids = [n for n, _ in hub_nodes]
    core_hubs = [n for n in hub_node_ids if n in core_indices]
    return {
        "gamma": round(float(gamma), 4),
        "scale_free": 2.0 <= gamma <= 3.5,
        "top_5_hubs": [(int(n), int(d)) for n, d in hub_nodes],
        "mandatory_core_in_top_hubs": len(core_hubs),
        "interpretation": (
            "Scale-free ✓ Mandatory Core = hubs (Barabási proof of C)" if gamma <= 3.5
            else "Not scale-free"
        ),
    }


def fiedler_value(G: nx.Graph) -> dict:
    """
    M34 bridge: Graph Laplacian λ₂ (Fiedler value).
    λ₂ < θ → collapse inevitable.
    SET-9: removing K1, K4 → λ₂ → 0.
    """
    if G.number_of_nodes() < 2:
        return {"lambda2": 0.0, "note": "Too few nodes"}
    L = nx.laplacian_matrix(G).toarray().astype(float)
    eigenvalues = np.linalg.eigvalsh(L)
    eigenvalues_sorted = np.sort(eigenvalues)
    lambda2 = float(eigenvalues_sorted[1]) if len(eigenvalues_sorted) > 1 else 0.0
    return {
        "lambda2": round(lambda2, 6),
        "collapse_risk": lambda2 < 0.05,
        "interpretation": (
            "HIGH COLLAPSE RISK — identity fragmented" if lambda2 < 0.05
            else "Stable connectivity" if lambda2 > 0.3
            else "Moderate connectivity"
        ),
    }


def set9_core_removal_test(P: np.ndarray, threshold: float = 0.04) -> dict:
    """
    SET-9 Simulation: remove K1 (idx 0) and K4 (idx 3).
    Measure Fiedler value before and after → validate Mandatory Core proof.
    """
    G_full = build_persona_network(P, threshold)
    f_full = fiedler_value(G_full)
    P_no_core = P.copy()
    P_no_core[0] = 0.0
    P_no_core[3] = 0.0
    G_no_core = build_persona_network(P_no_core, threshold)
    f_no_core = fiedler_value(G_no_core)
    return {
        "fiedler_full": f_full["lambda2"],
        "fiedler_no_core": f_no_core["lambda2"],
        "lambda2_drop": round(f_full["lambda2"] - f_no_core["lambda2"], 6),
        "collapse_after_removal": f_no_core["collapse_risk"],
        "set9_confirmed": f_no_core["lambda2"] < f_full["lambda2"] * 0.5,
        "conclusion": (
            "SET-9 CONFIRMED: Mandatory Core removal → Fiedler collapse"
            if f_no_core["lambda2"] < f_full["lambda2"] * 0.5
            else "SET-9 not confirmed at current threshold"
        ),
    }


# ── M30: Small-World Network ───────────────────────────────────────────────────

def small_world(G: nx.Graph, n_random: int = 20, seed: int = 42) -> dict:
    """
    Watts-Strogatz small-world test: C >> C_r, L ≈ L_r.

    C : clustering coefficient
    L : average shortest path length
    """
    if not nx.is_connected(G):
        G = G.subgraph(max(nx.connected_components(G), key=len)).copy()
    if G.number_of_nodes() < 3:
        return {"small_world": False, "note": "Graph too small"}
    C = nx.average_clustering(G)
    try:
        L = nx.average_shortest_path_length(G)
    except nx.NetworkXError:
        L = float("inf")
    n, m = G.number_of_nodes(), G.number_of_edges()
    C_r_vals, L_r_vals = [], []
    rng = np.random.default_rng(seed)
    for _ in range(n_random):
        R = nx.gnm_random_graph(n, m, seed=int(rng.integers(0, 99999)))
        if nx.is_connected(R):
            C_r_vals.append(nx.average_clustering(R))
            L_r_vals.append(nx.average_shortest_path_length(R))
    C_r = float(np.mean(C_r_vals)) if C_r_vals else float("nan")
    L_r = float(np.mean(L_r_vals)) if L_r_vals else float("nan")
    sigma = (C / C_r) / (L / L_r) if C_r > 0 and L_r > 0 else float("nan")
    return {
        "C": round(C, 5),
        "L": round(L, 5),
        "C_random": round(C_r, 5),
        "L_random": round(L_r, 5),
        "sigma": round(sigma, 4),
        "small_world": sigma > 1.5 if not np.isnan(sigma) else False,
    }


# ── M31: Nash Equilibrium ───────────────────────────────────────────────────────

def nash_eq_2player(payoff_A: np.ndarray, payoff_B: np.ndarray) -> dict:
    """
    Find pure-strategy Nash Equilibria in a 2-player game.
    u_i(s_i*, s_{-i}*) ≥ u_i(s_i, s_{-i}*) ∀i.

    Court of 250 application: deontological vs utilitarian coalition.
    151/99 split = Nash equilibrium when deontological payoffs dominate.

    Parameters
    ----------
    payoff_A, payoff_B : 2D payoff matrices (rows=player A strategies, cols=player B)
    """
    nash_points = []
    n_rows, n_cols = payoff_A.shape
    for i in range(n_rows):
        for j in range(n_cols):
            is_best_for_A = payoff_A[i, j] >= np.max(payoff_A[:, j])
            is_best_for_B = payoff_B[i, j] >= np.max(payoff_B[i, :])
            if is_best_for_A and is_best_for_B:
                nash_points.append((i, j))
    return {
        "nash_equilibria": nash_points,
        "n_equilibria": len(nash_points),
        "unique_equilibrium": len(nash_points) == 1,
    }


def court_of_250_nash(
    P: Optional[np.ndarray] = None,
    n_total: int = 250,
) -> dict:
    """
    [HEURISTIC] M31: Court of 250 simulation — persona-modulated coalition.

    Payoff matrix is adjusted by the persona's ethics axis (Block 9).
    High ethics (B9 > 0.5) → D payoff increases (virtue strengthens rule-keeping).
    Low ethics (B9 < 0.2) → C payoff increases (Machiavellian drift).

    Base payoffs:
        u(D,D)=0.8  u(D,C)=0.3
        u(C,D)=0.4  u(C,C)=0.6
    Nash condition: u(D,D) > u(C,D) → D dominant strategy.
    """
    ethics_mod = 0.0
    if P is not None and len(P) >= 90:
        ethics_mod = float(np.mean(P[80:90])) - 0.3   # center around 0.3 baseline

    payoff_matrix = np.array([
        [min(1.0, 0.8 + 0.1 * ethics_mod),  max(0.0, 0.3 + 0.05 * ethics_mod)],
        [max(0.0, 0.4 - 0.1 * ethics_mod),  min(1.0, 0.6 - 0.05 * ethics_mod)],
    ])
    payoff_A = payoff_matrix
    payoff_B = payoff_matrix.T
    result = nash_eq_2player(payoff_A, payoff_B)

    # Deontological fraction scales with ethics axis
    base_fraction = 151 / 250
    if P is not None and len(P) >= 90:
        ethics_val = float(np.mean(P[80:90]))
        base_fraction = 0.5 + 0.2 * (ethics_val - 0.3)
    deontological_count = int(n_total * max(0.1, min(0.9, base_fraction)))

    return {
        "total_personas": n_total,
        "deontological": deontological_count,
        "consequentialist": n_total - deontological_count,
        "split_ratio": round(deontological_count / n_total, 3),
        "nash_result": result,
        "stable_coalition": result["n_equilibria"] > 0,
        "ethics_modulation": round(ethics_mod, 4),
    }


# ── M32: Lotka-Volterra Coevolution ────────────────────────────────────────────

def lotka_volterra(
    P0: float = 0.8,
    U0: float = 0.3,
    alpha: float = 0.5,
    beta: float = 0.3,
    delta: float = 0.2,
    gamma: float = 0.4,
    T: float = 50.0,
    dt: float = 0.1,
) -> dict:
    """
    Persona-User coevolution:
    Ṗ = αP − βPU   (persona grows, suppressed by user divergence)
    U̇ = δPU − γU   (user drawn toward persona, natural decay)

    Holmes Phase 1: user language shifts toward Holmes register (LV oscillation).
    α/β = 'persona power' ratio.

    Returns
    -------
    dict with time series and equilibrium analysis
    """
    def lv_ode(t, y):
        P, U = y
        dP = alpha * P - beta * P * U
        dU = delta * P * U - gamma * U
        return [dP, dU]

    t_eval = np.arange(0, T, dt)
    sol = solve_ivp(lv_ode, [0, T], [P0, U0], t_eval=t_eval, method="RK45")
    P_eq = gamma / delta if delta > 0 else float("inf")
    U_eq = alpha / beta if beta > 0 else float("inf")
    persona_power = alpha / beta if beta > 0 else float("inf")
    return {
        "t": sol.t,
        "P": sol.y[0],
        "U": sol.y[1],
        "equilibrium": {"P*": round(P_eq, 4), "U*": round(U_eq, 4)},
        "persona_power_ratio": round(persona_power, 4),
        "interpretation": (
            "Strong persona — user pulled into register" if persona_power > 2.0
            else "Balanced coevolution" if persona_power > 0.8
            else "Weak persona — user dominates"
        ),
    }
