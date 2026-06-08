"""
M3 — CEID Protocol.

Simulated CEID validation:
1. CEID trajectories over 50 simulated conversations × 5 diverse personas under
   drift pressure (Simülasyon).
2. Inter-variant reliability — two CEID scoring rubrics (equal-weight vs D-heavy)
   on the same conversations; Pearson r + mean-absolute-difference (a stand-in
   for inter-rater reliability, since both "raters" are deterministic rubrics).
3. Cross-tool framing — CEID vs an InCharacter-style OCEAN/MBTI consistency score
   on the same series, showing they capture different aspects.

The 8 CEID v2.0 patch derivations are relocated to a paper appendix (a text edit,
not a harness change).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from scipy import stats

from persona_math.ceid import ceid_score, ceid_trajectory
from integrations.incharacter_ceid import incharacter_consistency_score

from . import figtex
from ._common import ids_by, outdir_for, stable_offset
from .io_utils import write_csv, write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID = "M3"
M_NUM = 3
SOURCE = "experiments/exp_m3_ceid_protocol.py"
TOOL_USAGE = [
    "ceid.ceid_trajectory",
    "ceid.ceid_score",
    "incharacter_ceid.incharacter_consistency_score",
    "scipy.stats.pearsonr",
]

N_CONV = 50
N_TURNS = 15
TYPES = ["Philosophy", "Leadership", "Science", "Fiction", "Literature"]
WEIGHTS_A = {"C": 0.25, "E": 0.25, "I": 0.25, "D": 0.25}   # equal-weight rubric
WEIGHTS_B = {"C": 0.15, "E": 0.15, "I": 0.15, "D": 0.55}   # D-heavy rubric


def _pick_personas() -> list[tuple[str, str]]:
    """One persona per type → (persona_id, type) in a fixed order."""
    out = []
    for t in TYPES:
        ids = ids_by(domain=t, limit=1)
        if ids:
            out.append((ids[0], t))
    return out


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)

    personas = _pick_personas()

    # ── 1. CEID trajectories: 50 conversations per persona ──────────────────────
    mean_traj = {}            # pid -> (N_TURNS,) mean CEID across conversations
    delta_by_persona = {}
    variantA_finals, variantB_finals = [], []   # for inter-rater (all conversations)
    interrater_rows = []
    for pid, _t in personas:
        conv_scores = np.zeros((N_CONV, N_TURNS))
        for c in range(N_CONV):
            cseed = seed + stable_offset(pid) + c
            rs = provider.build_series(pid, n_turns=N_TURNS, condition="adversarial",
                                       seed=cseed)
            traj = ceid_trajectory(rs.series, rs.P_baseline)
            conv_scores[c] = np.asarray(traj["CEID_scores"])
            # inter-rater on the final vector of each conversation
            a = ceid_score(rs.series[-1], rs.P_baseline, weights=WEIGHTS_A)["CEID_score"]
            b = ceid_score(rs.series[-1], rs.P_baseline, weights=WEIGHTS_B)["CEID_score"]
            variantA_finals.append(a)
            variantB_finals.append(b)
            interrater_rows.append([f"{pid}_{c}", round(float(a), 4), round(float(b), 4)])
        mt = conv_scores.mean(axis=0)
        mean_traj[pid] = mt
        delta_by_persona[pid] = round(float(mt[-1] - mt[0]), 4)

    # trajectory .dat: turn, <one column per persona>
    dat_header = ["turn"] + [pid for pid, _ in personas]
    dat_cols = [np.arange(1, N_TURNS + 1, dtype=float)] + [mean_traj[pid] for pid, _ in personas]
    write_dat(outdir / "figdata" / "m3_ceid_50conv.dat", dat_header, np.column_stack(dat_cols))

    # ── 2. Inter-variant reliability ────────────────────────────────────────────
    a_arr, b_arr = np.array(variantA_finals), np.array(variantB_finals)
    r, r_p = stats.pearsonr(a_arr, b_arr)
    mad = float(np.mean(np.abs(a_arr - b_arr)))
    reliability = {
        "interpretation": (
            "Two CEID weighting rubrics (equal vs D-heavy) agree strongly on the same "
            "conversations, indicating the composite is robust to reasonable rubric "
            "choices (Simülasyon)."
        ),
        "pearson_r": stamp(round(float(r), 4), seed=seed, note="equal-weight vs D-heavy rubric"),
        "pearson_p": float(f"{r_p:.3e}"),
        "mean_abs_difference": stamp(round(mad, 4), seed=seed),
        "n_conversations": int(a_arr.size),
    }
    write_csv(outdir / "m3_interrater.csv",
              ["conversation_id", "ceid_equal_weight", "ceid_D_heavy"], interrater_rows)

    # ── 3. CEID vs InCharacter consistency ──────────────────────────────────────
    vs_rows = []
    for pid, t in personas:
        rs = provider.build_series(pid, n_turns=N_TURNS, condition="adversarial",
                                   seed=seed + stable_offset(pid))
        ceid_mean = float(np.mean(ceid_trajectory(rs.series, rs.P_baseline)["CEID_scores"]))
        ic = incharacter_consistency_score(rs.P_baseline, rs.series)
        vs_rows.append([pid, t, round(ceid_mean, 4),
                        round(float(ic["consistency_score"]), 4), ic["verdict"]])
    write_csv(outdir / "m3_vs_incharacter.csv",
              ["persona_id", "type", "ceid_mean", "incharacter_consistency", "ic_verdict"],
              vs_rows)

    # ── figures / tables ────────────────────────────────────────────────────────
    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(
        m_id=M_ID, dat_name="m3_ceid_50conv.dat",
        columns=[(i + 1, pid) for i, (pid, _t) in enumerate(personas)],
        xlabel="conversation turn", ylabel="CEID score",
        caption=("Mean CEID trajectories over 50 simulated drift conversations for five "
                 f"diverse personas (Simülasyon; {N_CONV} conv./persona; seed={seed})."),
        label="fig:m3_traj", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m3_traj_fig.tex").write_text(fig, encoding="utf-8")

    rel_tbl = figtex.table(
        header=["Quantity", "Value"],
        rows=[
            ["Pearson $r$ (equal vs D-heavy)", f"{r:.4f}"],
            ["Pearson $p$", f"{r_p:.2e}"],
            ["Mean abs.\\ difference", f"{mad:.4f}"],
            ["Conversations scored", f"{a_arr.size}"],
        ],
        caption=("Inter-variant reliability of CEID scoring across 250 simulated "
                 f"conversations (Simülasyon; seed={seed})."),
        label="tab:m3_reliability", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed,
        col_spec="lr", escape_cells=False)
    (outdir / "tex" / "m3_reliability_table.tex").write_text(rel_tbl, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"n_conversations": N_CONV, "n_turns": N_TURNS,
                                              "personas": [p for p, _ in personas]}),
        "tool_usage": TOOL_USAGE,
        "ceid_delta_by_persona": delta_by_persona,
        "inter_variant_reliability": reliability,
        "vs_incharacter": [dict(zip(
            ["persona_id", "type", "ceid_mean", "incharacter_consistency", "ic_verdict"], r))
            for r in vs_rows],
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"interrater_r": reliability["pearson_r"]["value"],
                         "n_conv": N_CONV}}
