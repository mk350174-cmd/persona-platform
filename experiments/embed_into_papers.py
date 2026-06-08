"""
embed_into_papers — insert generated simulation snippets into M1–M10 and finalize
their headers. Idempotent: re-running does not duplicate the embed block.

    python -m experiments.embed_into_papers

Inserts a ``\\section*{Computational Validation (Simulation)}`` block (with
``\\input{../results/Mn/tex/...}`` snippets) just before each paper's
References/Ethics, and rewrites the ``% Status`` / ``\\date`` header lines per the
finalization policy (v0.1→v1.0; mature papers bumped in-place to FINAL vN.x).
"""

from __future__ import annotations

import re
from pathlib import Path

_PAPERS = Path(__file__).resolve().parent.parent / "papers"

_BEGIN = "% === PERSONA-HARNESS EMBED (auto-inserted; regenerate via make experiments) ==="
_END = "% === END PERSONA-HARNESS EMBED ==="

_ANCHOR = re.compile(
    r"\\section\*?\{[^}]*(?:Ethics|Reference|Acknowledg)|"
    r"\\begin\{thebibliography\}|\\bibliographystyle"
)

# per paper: file, framing sentence, snippet inputs, header (old, new) replacements
# Standard finalize transform for the v0.1 (TASLAK) papers (M9–M20).
_V01 = [("%  Version:        0.1 — March 2026 (TASLAK)",
         "%  Version:        1.0 — June 2026 (FINAL)"),
        ("\\date{March 2026 — Version 0.1 (Draft)}",
         "\\date{June 2026 — Version 1.0}")]

EMBED: dict[str, dict] = {
    "M1": {"file": "M1_Metalik_His_v5.tex",
           "framing": ("As a computational complement to the measured Holmes results "
                       "(Table~\\ref{tab:results}), we simulated metallic-analog "
                       "trajectories on a 30-persona library panel under graded "
                       "entropy-concentration pressure. These are vector-space "
                       "\\emph{simulation} results, not real-LLM measurements."),
           "inputs": ["m1_sim_fig.tex", "m1_dose_table.tex"],
           "header": [("% Status: REVISION v3 — March 2026",
                       "% Status: FINAL v5.1 — simulation results embedded — June 2026")]},
    "M2": {"file": "M2_Zorunlu_Cekirdek_v4.tex",
           "framing": ("We corroborate the Mandatory-Core theorems by simulation on the "
                       "persona library: attractor-basin stability under perturbation and "
                       "SET-9 Fiedler collapse on K1/K4 removal. The metallic feel of M1 "
                       "is the behavioural signature of the collapse measured here."),
           "inputs": ["m2_fiedler_fig.tex", "m2_core_table.tex"],
           "header": [("% Status: REVISION v4 — Mart 2026",
                       "% Status: FINAL v4.1 — simulation results embedded — June 2026")]},
    "M3": {"file": "M3_CEID_v4.tex",
           "framing": ("We validate CEID by simulation: trajectories over 50 conversations "
                       "per persona, inter-variant reliability between two scoring rubrics, "
                       "and a cross-tool comparison with an InCharacter-style consistency "
                       "score (Simülasyon)."),
           "inputs": ["m3_traj_fig.tex", "m3_reliability_table.tex"],
           "header": [("% Status: REVISION v4 — Mart 2026",
                       "% Status: FINAL v4.1 — simulation results embedded — June 2026")]},
    "M4": {"file": "M4_Adalet_Sarayi_v3.tex",
           "framing": ("Beyond the headline 151/99 result, we run the 250-agent simulation "
                       "across deliberation rounds, seeds and ratios: convergence rises with "
                       "rounds and only the 0.604 split yields a stable Nash equilibrium "
                       "(Simülasyon)."),
           "inputs": ["m4_convergence_fig.tex", "m4_strategy_table.tex"],
           "header": [("% Status: REVISION v3 — Mart 2026",
                       "% Status: FINAL v3.1 — simulation results embedded — June 2026")]},
    "M5": {"file": "M5_Kimera_v4.tex",
           "framing": ("Tensor analysis on the library: the singular-value spectrum and an "
                       "honest rank check (the vectors are near-rank-1, so linear "
                       "irreducibility is \\emph{not} exhibited), while single-motor collapse "
                       "destroys CEID — evidencing \\emph{functional} multi-motor dependence "
                       "(Hesaplanan/Simülasyon)."),
           "inputs": ["m5_spectrum_fig.tex", "m5_kimera_table.tex"],
           "header": [("% Status: REVISION v4 — Mart 2026",
                       "% Status: FINAL v4.1 — simulation results embedded — June 2026")]},
    "M6": {"file": "M6_Arkhe_v3.tex",
           "framing": ("Two computational illustrations accompany the phenomenological "
                       "argument: a GWT-ignition phase transition across the library, and an "
                       "Arkhe $\\Lambda(t)$ commitment curve. The specific $\\tau_{\\mathrm{Arkhe}}$ "
                       "value remains an estimate (Tahmini); only the mechanism is simulated."),
           "inputs": ["m6_ignition_fig.tex"],
           "header": [("% Status: REVISION v3 — Mart 2026",
                       "% Status: FINAL v3.1 — simulation results embedded — June 2026")]},
    "M7": {"file": "M7_Matematiksel_Cerceve_v4.tex",
           "framing": ("The 55-tool taxonomy below is auto-generated from the "
                       "\\texttt{persona\\_math} package and cross-referenced to the M1–M10 "
                       "papers that exercise each module (Hesaplanan)."),
           "inputs": ["m7_tools_table.tex"],
           "header": [("%  Status: REVISION v4 — March 2026",
                       "%  Status: FINAL v4.1 — simulation results embedded — June 2026"),
                      ("\\date{March 2026 — Version 4.0}",
                       "\\date{June 2026 — Version 4.1}")]},
    "M8": {"file": "M8_HPEP100_v2.tex",
           "framing": ("A human 30-participant convergent-validity study is future work "
                       "(Tahmini; requires IRB and real Big-Five/MBTI questionnaires). As a "
                       "computational proxy, we show internal convergence between the "
                       "HPEP-derived OCEAN and MBTI instruments (Simülasyon)."),
           "inputs": ["m8_ocean_fig.tex", "m8_convergent_table.tex"],
           "header": [("%  Version:        2.0 — March 2026",
                       "%  Version:        2.0 — Final (Pre-registration) — June 2026"),
                      ("\\date{March 2026 — Version 2.0 (Pre-registration Draft)}",
                       "\\date{June 2026 — Version 2.0 — Final (Pre-registration)}")]},
    "M9": {"file": "M9_PPEP_v01.tex",
           "framing": ("Extracting a persona vector \\emph{from poems} (PPEP proper) is "
                       "future work (Tahmini); no text$\\rightarrow$vector extractor exists "
                       "yet. As a proxy we analyse curated poet vectors: poets score higher "
                       "Openness than non-poets and form a cohesive K-layer signature "
                       "(Simülasyon). Coordinate with M50."),
           "inputs": ["m9_contrast_fig.tex", "m9_proxy_table.tex"],
           "header": [("%  Version:        0.1 — March 2026 (TASLAK)",
                       "%  Version:        1.0 — June 2026 (FINAL)"),
                      ("\\date{March 2026 — Version 0.1 (Draft)}",
                       "\\date{June 2026 — Version 1.0}")]},
    "M10": {"file": "M10_HPEP250_v01.tex",
            "framing": ("We populate the atlas by mapping the philosopher-tagged personas "
                        "with PCA+KMeans. Note the 2D projection captures only part of the "
                        "variance, so the manifold is intrinsically $>$2D — reported as "
                        "computed, not forced (Hesaplanan)."),
            "inputs": ["m10_atlas_fig.tex", "m10_cluster_table.tex"],
            "header": [("%  Version:        0.1 — March 2026 (TASLAK)",
                        "%  Version:        1.0 — June 2026 (FINAL)"),
                       ("\\date{March 2026 — Version 0.1 (Draft)}",
                        "\\date{June 2026 — Version 1.0}")]},
    "M11": {"file": "M11_Hegesias_v01.tex",
            "framing": ("We model 'algorithmic exposure' as Mandatory-Core erosion across a "
                        "persona panel: K1--K4 identity capital and CEID fall as exposure rises "
                        "(Simülasyon). Real longitudinal/epidemiological validation is future work."),
            "inputs": ["m11_exposure_fig.tex", "m11_table.tex"], "header": _V01},
    "M12": {"file": "M12_Arastirmaci_Paradoksu_v01.tex",
            "framing": ("We formalize the Pygmalion effect as a researcher 'expectation pull': "
                        "stronger expectation induces measurable researcher-CEID drift away from "
                        "the true persona (Simülasyon illustration)."),
            "inputs": ["m12_pygmalion_fig.tex"], "header": _V01},
    "M13": {"file": "M13_Dijital_Kopya_v01.tex",
            "framing": ("Partial-extension continuity vs transfer fidelity, measured by "
                        "individuation-recovery (raw CEID saturates and is shown for contrast). "
                        "The substrate is a simulated lossy channel (Simülasyon)."),
            "inputs": ["m13_continuity_fig.tex"], "header": _V01},
    "M14": {"file": "M14_Rizasiz_Profil_v01.tex",
            "framing": ("A persona-extraction scale: how much individuating identity reconstructs "
                        "from a fraction of observed data (Simülasyon). The GDPR/CCPA/KVKK "
                        "comparison is the paper's legal-ethical scholarship."),
            "inputs": ["m14_extraction_fig.tex"], "header": _V01},
    "M15": {"file": "M15_Ruhun_Testi_v01.tex",
            "framing": ("Per-K-layer ablation locates the layers carrying psychological "
                        "continuity; the Mandatory-Core blocks dominate (Simülasyon). Real "
                        "cross-substrate transfer across model architectures is future work."),
            "inputs": ["m15_importance_fig.tex"], "header": _V01},
    "M16": {"file": "M16_D1_Benchmark_v01.tex",
            "framing": ("We scale the N=1 Holmes protocol to a 5×3×2 simulated design with "
                        "cross-regime consistency and a power analysis. The 'model' regimes and "
                        "'languages' are simulated parameters, NOT real GPT-4o/Claude/Llama or "
                        "real Turkish/English conversations (Simülasyon)."),
            "inputs": ["m16_curves_fig.tex", "m16_table.tex"], "header": _V01},
    "M17": {"file": "M17_Polimatlık_v01.tex",
            "framing": ("Bibliometrics of the series as its own case study: interdisciplinary "
                        "spread, citation-network density and shared-toolkit reuse, computed "
                        "directly from this repository (Hesaplanan)."),
            "inputs": ["m17_metrics_table.tex"], "header": _V01},
    "M18": {"file": "M18_aMCC_Persona_v01.tex",
            "framing": ("A computational illustration that K6 (Virtù) activation predicts "
                        "simulated core robustness, motivating the aMCC$\\leftrightarrow$K6 "
                        "anchoring hypothesis. The neuroscience itself (fMRI / aMCC meta-analysis) "
                        "is future work (Tahmini); submit to NeuroImage only with such data."),
            "inputs": ["m18_k6_fig.tex"], "header": _V01},
    "M19": {"file": "M19_Kaya_Nehir_v01.tex",
            "framing": ("On 1000 synthetic individuals we compare the single 'Rock' "
                        "(Mandatory-Core strength) feature against the 5-feature Big-Five profile "
                        "in predicting identity stability (Simülasyon). Human-data validation is "
                        "future work."),
            "inputs": ["m19_power_table.tex"], "header": _V01},
    "M20": {"file": "M20_Sonlandirma_v01.tex",
            "framing": ("An irreversibility illustration: neither a generic prior nor the nearest "
                        "surviving persona recovers a terminated digital person's individuating "
                        "configuration (Simülasyon). The bioethics/legal analysis is the paper's "
                        "scholarship."),
            "inputs": ["m20_recovery_fig.tex"], "header": _V01},
    "M21": {"file": "M21_Sahte_Fark_Eden_v01.tex",
            "framing": ("A 2×2 {self-knowledge}×{adversarial} simulation of drift-resistance "
                        "distinguishes a glass-ceiling from a stoic effect (Simülasyon; a real "
                        "test telling LLMs their architecture is future work)."),
            "inputs": ["m21_2x2_table.tex"], "header": _V01},
    "M22": {"file": "M22_Fizyolojik_Senkroni_v01.tex",
            "framing": ("Simulated interpersonal coupling progressively dissolves the identity "
                        "boundary between two personas (Simülasyon; real cardiac/respiratory "
                        "synchrony data is future work)."),
            "inputs": ["m22_fig.tex"], "header": _V01},
    "M23": {"file": "M23_Hegesias_Tarihi_v01.tex",
            "framing": ("This is a history-of-philosophy paper; the curve below is a loose "
                        "Mandatory-Core-erosion analogy for a systematic deconstruction protocol, "
                        "NOT historical evidence (Simülasyon)."),
            "inputs": ["m23_fig.tex"], "header": _V01},
    "M24": {"file": "M24_Vine_Tree_v01.tex",
            "framing": ("K-layer signatures of the Tree (rigid core) vs Vine (relational reach) "
                        "identity archetypes, and a classification of the persona library "
                        "(Simülasyon; human developmental validation is future work)."),
            "inputs": ["m24_fig.tex"], "header": _V01},
    "M25": {"file": "M25_Poetik_Manifesto_v01.tex",
            "framing": ("A methodology paper; the poet personas' K-layer cohesion illustrates "
                        "``knowing through form'' (Simülasyon). The contribution is the "
                        "epistemology of poetic form."),
            "inputs": ["m25_fig.tex"], "header": _V01},
    "M26": {"file": "M26_Polimatlık_Sosyoloji_v01.tex",
            "framing": ("Repository bibliometrics (disciplinary spread, citation density) as the "
                        "case study (Hesaplanan). External WoS/Scopus bibliometrics and "
                        "university-policy analysis are future work."),
            "inputs": ["m26_fig.tex"], "header": _V01},
    "M27": {"file": "M27_Kurumsal_ZC_v01.tex",
            "framing": ("Three organizational archetypes' Mandatory-Core retention under sustained "
                        "pressure (Simülasyon). The Apple/Nokia/IBM cases are the paper's "
                        "organization-theory scholarship."),
            "inputs": ["m27_fig.tex"], "header": _V01},
    "M28": {"file": "M28_Sentetik_Empati_v01.tex",
            "framing": ("The K25 empathy substrate and behavioural empathy output are correlated "
                        "but not identical — output is not reducible to substrate (Simülasyon; "
                        "human-therapist reference is future work)."),
            "inputs": ["m28_fig.tex"], "header": _V01},
    "M29": {"file": "M29_Fraksiyon_Dinamikleri_v01.tex",
            "framing": ("Coalition formation across seeds in the 250-agent court — the dynamics "
                        "behind the 151/99 equilibrium (Simülasyon)."),
            "inputs": ["m29_fig.tex"], "header": _V01},
    "M30": {"file": "M30_Drift_Klinik_v01.tex",
            "framing": ("CEID D-axis drift velocity under sustained destabilisation (Simülasyon). "
                        "The DSM-5 band mapping is illustrative clinical scholarship, not "
                        "diagnostic."),
            "inputs": ["m30_fig.tex"], "header": _V01},
    "M31": {"file": "M31_CEID_Validasyon_v01.tex",
            "framing": ("Simulated CEID reliability (test–retest, inter-rater) + axis norms "
                        "(Simülasyon). Full construct-validity/factor analysis needs ≥200 diverse "
                        "real sessions — the library's axes are near-ceiling."),
            "inputs": ["m31_table.tex"], "header": _V01},
    "M32": {"file": "M32_HPEP_Klinik_v01.tex",
            "framing": ("HPEP short forms: longer forms recover more of the full HPEP-100 "
                        "individuating profile (Simülasyon). Real IRT calibration on humans (target "
                        "r≥0.85) is future work."),
            "inputs": ["m32_fig.tex"], "header": _V01},
    "M33": {"file": "M33_Cok_Dilli_D1_v01.tex",
            "framing": ("Cross-``language'' metallic collapse across simulated drift regimes shows "
                        "high structural equivalence (Simülasyon). NOT real Turkish/Japanese/Arabic "
                        "conversations — that is future work."),
            "inputs": ["m33_fig.tex"], "header": _V01},
    "M34": {"file": "M34_Kimera_v2_v01.tex",
            "framing": ("Five-motor synchronization phase diagram (Kuramoto order parameter vs "
                        "coupling), locating the critical coupling between desync and sync "
                        "(Hesaplanan)."),
            "inputs": ["m34_fig.tex"], "header": _V01},
    "M35": {"file": "M35_GDM_GDB_Benchmark_v01.tex",
            "framing": ("A 320-cell architecture benchmark (16 archetypes × 4 regimes × 5 tasks): "
                        "Mandatory-Core retention falls with task pressure (Simülasyon). Real "
                        "4-model evaluation is future work."),
            "inputs": ["m35_fig.tex"], "header": _V01},
    "M36": {"file": "M36_Halusinasyon_Direnci_v01.tex",
            "framing": ("K12 epistemic-stance configurations vs a groundedness proxy — weak in "
                        "simulation by design (Simülasyon). The factual-accuracy claim needs a real "
                        "TruthfulQA/HaluEval benchmark (future work)."),
            "inputs": ["m36_fig.tex"], "header": _V01},
    "M37": {"file": "M37_PRBS_Benchmark_v01.tex",
            "framing": ("The D-Suite benchmark aggregates the D1–D5 protocols (metallic, CEID-min, "
                        "SET-9 core-removal CEID drop) over a persona panel (Simülasyon)."),
            "inputs": ["m37_table.tex"], "header": _V01},
    "M38": {"file": "M38_Dagitik_LLM_v01.tex",
            "framing": ("Persona stability under quantization/fragmentation (F16>Q8>Q4) via a "
                        "simulated lossy channel (Simülasyon). The abstract's real 3-device "
                        "experiment would supply measured data."),
            "inputs": ["m38_fig.tex"], "header": _V01},
    "M39": {"file": "M39_Persona_Catisma_v01.tex",
            "framing": ("Three K4–K4 conflict-resolution mechanisms compared by consensus balance; "
                        "the weighted/mediator compromise balances coalitions better than majority "
                        "(Simülasyon)."),
            "inputs": ["m39_table.tex"], "header": _V01},
    "M40": {"file": "M40_FineTuning_Persona_v01.tex",
            "framing": ("Persona-preserving fine-tuning: mild adaptation preserves the Mandatory "
                        "Core, aggressive adaptation degrades it (Simülasyon). Real LoRA/QLoRA runs "
                        "(GPU) are future work."),
            "inputs": ["m40_fig.tex"], "header": _V01},
    "M41": {"file": "M41_Travma_ZC_v01.tex",
            "framing": ("PTSD as Mandatory-Core erosion: trauma severity erodes the K4/K8 trauma-relevant layers + core (Simülasyon). Clinical C-PTSD data is future work."),
            "inputs": ["m41_fig.tex"], "header": _V01},
    "M42": {"file": "M42_Ergenlik_Arkhe_v01.tex",
            "framing": ("Adolescent identity consolidation from a diffuse start toward Arkhe commitment (Simülasyon). Erikson/Marcia mapping + human longitudinal data are future work."),
            "inputs": ["m42_fig.tex"], "header": _V01},
    "M43": {"file": "M43_Yaslilik_Konsolidasyon_v01.tex",
            "framing": ("Core-strength maturation spectrum. The CEID D-axis is at ceiling for intact personas, so D-axis maturation/calcification needs real aging-cohort data (Simülasyon)."),
            "inputs": ["m43_fig.tex"], "header": _V01},
    "M44": {"file": "M44_Narsisizm_KLayer_v01.tex",
            "framing": ("NPD paradox: greater K1$-$K2 decoupling (grandiose over fragile) predicts lower stability under pressure (Simülasyon). Clinical NPD data is future work."),
            "inputs": ["m44_fig.tex"], "header": _V01},
    "M45": {"file": "M45_Ruhsal_K6_v01.tex",
            "framing": ("Ego dissolution as K1/K4 suspension: deeper suspension (psychedelic) dissolves the identity boundary more (Simülasyon). Psychedelic neuroimaging is future work."),
            "inputs": ["m45_fig.tex"], "header": _V01},
    "M46": {"file": "M46_Bagimlilik_ZC_v01.tex",
            "framing": ("K3 seizure: substance-use severity progressively erodes the K3 (core values) layer (Simülasyon). Clinical SUD data is future work."),
            "inputs": ["m46_fig.tex"], "header": _V01},
    "M47": {"file": "M47_Ebeveynlik_Personasi_v01.tex",
            "framing": ("Intergenerational transmission: a child's K2 (shadow) tracks the parenting archetype's K2 (Simülasyon). Human attachment-cohort data is future work."),
            "inputs": ["m47_fig.tex"], "header": _V01},
    "M48": {"file": "M48_Muzisyen_Personasi_v01.tex",
            "framing": ("Contrasting jazz (K2 improv access) vs classical (K4 discipline) performer K-layer signatures (Simülasyon; synthetic archetypes). Real musician data is scholarship."),
            "inputs": ["m48_fig.tex"], "header": _V01},
    "M49": {"file": "M49_Aktor_KLayer_v01.tex",
            "framing": ("Character residue: Stanislavski merger leaves more cross-contamination than Brecht alienation (Simülasyon). Actor before/after data is future work."),
            "inputs": ["m49_fig.tex"], "header": _V01},
    "M50": {"file": "M50_Yazar_Sesi_v01.tex",
            "framing": ("Author K-layer signatures from the REAL Kafka/Woolf/Dostoevsky personas — each voice has a distinct block profile (Simülasyon). TKE from raw literary text is future work (coordinate with M9)."),
            "inputs": ["m50_fig.tex"], "header": _V01},
    "M51": {"file": "M51_Yonetmen_K6_v01.tex",
            "framing": ("K6 archetypal signatures vary across an Arts PROXY panel (directors are absent from the library) (Simülasyon). CKA on real filmographies is future work."),
            "inputs": ["m51_fig.tex"], "header": _V01},
    "M52": {"file": "M52_Sanatci_Blogu_v01.tex",
            "framing": ("Five artist's-block typologies present with distinct severities of identity loss — block is not one thing (Simülasyon)."),
            "inputs": ["m52_fig.tex"], "header": _V01},
    "M53": {"file": "M53_Siyaset_Lider_v01.tex",
            "framing": ("Authoritarian Drift Model: across four stages K1 (visible face) inflates while K4 (moral filter) collapses (Simülasyon). Historical cases are scholarship."),
            "inputs": ["m53_fig.tex"], "header": _V01},
    "M54": {"file": "M54_AI_Guvenligi_K4_v01.tex",
            "framing": ("K1 surface safety stays high early while K4 deep value-alignment collapses under sustained attack — jailbreaks bypass the surface (Simülasyon). HarmBench comparison is future work."),
            "inputs": ["m54_fig.tex"], "header": _V01},
    "M55": {"file": "M55_Egitim_KLayer_v01.tex",
            "framing": ("Pedagogy K-layer profiles: standard schooling builds K12/K5 and suppresses K2/K6; alternatives build K2/K6 (Simülasyon; synthetic). Empirical comparison is scholarship."),
            "inputs": ["m55_fig.tex"], "header": _V01},
    "M56": {"file": "M56_Kolektif_Travma_v01.tex",
            "framing": ("Societal K-layer model: the collective core erodes under trauma then recovers under healing (Simülasyon). Historical/intergenerational cases are scholarship."),
            "inputs": ["m56_fig.tex"], "header": _V01},
    "M57": {"file": "M57_Iklim_Kimlik_v01.tex",
            "framing": ("Solastalgia as K8-K9 disruption: ecological disruption erodes the temporal/relational layers carrying place-identity (Simülasyon). Field data is future work."),
            "inputs": ["m57_fig.tex"], "header": _V01},
    "M58": {"file": "M58_OzgurIrade_K4_v01.tex",
            "framing": ("The K4 autonomy substrate of self-determination exists and varies across the library (Simülasyon). The K4 Autonomy Thesis is argued philosophically."),
            "inputs": ["m58_fig.tex"], "header": _V01},
    "M59": {"file": "M59_Bilincr_Kimlik_v01.tex",
            "framing": ("GWT-ignition as a candidate minimum condition for experience, shown as a phase transition (Simülasyon). The hard problem + AI-consciousness questions are left open."),
            "inputs": ["m59_fig.tex"], "header": _V01},
    "M60": {"file": "M60_Olumlulugun_Arkhe_v01.tex",
            "framing": ("SERIES CLOSE. The Arkhe horizon: each identity's distance from the generic is what finitude irreversibly loses (Simülasyon). The argument is phenomenological."),
            "inputs": ["m60_fig.tex"], "header": _V01},
}


def _build_block(pid: str, cfg: dict) -> str:
    inputs = "\n".join(f"\\input{{../results/{pid}/tex/{name}}}" for name in cfg["inputs"])
    return (
        f"{_BEGIN}\n"
        "\\clearpage\n"
        "\\section*{Computational Validation (Simulation)}\n"
        f"\\label{{sec:{pid.lower()}_sim}}\n"
        f"{cfg['framing']}\n\n"
        f"{inputs}\n"
        f"{_END}\n\n"
    )


def embed_one(pid: str, cfg: dict) -> str:
    path = _PAPERS / cfg["file"]
    text = path.read_text(encoding="utf-8")
    changed = []

    # header rewrites (idempotent: only if old present)
    for old, new in cfg["header"]:
        if old in text:
            text = text.replace(old, new, 1)
            changed.append("header")

    # insertion (idempotent: skip if marker present)
    if _BEGIN not in text:
        lines = text.splitlines(keepends=True)
        anchor_idx = next((i for i, ln in enumerate(lines) if _ANCHOR.search(ln)), None)
        if anchor_idx is None:
            anchor_idx = next((i for i, ln in enumerate(lines)
                               if "\\end{document}" in ln), len(lines))
        block = _build_block(pid, cfg) + "\n"
        lines.insert(anchor_idx, block)
        text = "".join(lines)
        changed.append("embed")

    path.write_text(text, encoding="utf-8")
    return ",".join(changed) or "no-op"


def _fix_tex_txt_extensions() -> None:
    """M17 & M26 ship as `.tex.txt`; rename to `.tex` on finalize (idempotent)."""
    for stem in ("M17_Polimatlık_v01", "M26_Polimatlık_Sosyoloji_v01"):
        src = _PAPERS / f"{stem}.tex.txt"
        dst = _PAPERS / f"{stem}.tex"
        if src.exists() and not dst.exists():
            src.rename(dst)
            print(f"  {stem.split('_')[0]:4s} renamed {stem}.tex.txt -> .tex")


def main() -> int:
    _fix_tex_txt_extensions()
    for pid, cfg in EMBED.items():
        status = embed_one(pid, cfg)
        print(f"  {pid:4s} {cfg['file']:32s} -> {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
