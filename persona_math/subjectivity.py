"""M44-M46: Subjectivity & Epistemic Limits"""

import numpy as np


def self_awareness_index(P: np.ndarray) -> dict:
    """M44 — Self-awareness: meta-cognitive layer activation.
    K24 (index 23) = self-referential layer; K100 (index 99) = terminal singularity.
    identity_coherence = 1 - std(P); self_awareness = (P[23]+P[99])/2 * coherence.
    """
    meta_layer = float(P[23])
    terminal   = float(P[99])
    identity_coherence = float(1.0 - np.std(P))
    index = (meta_layer + terminal) / 2.0 * identity_coherence

    if index < 0.2:
        level = "absent"
    elif index < 0.4:
        level = "emerging"
    elif index < 0.7:
        level = "present"
    else:
        level = "acute"

    return {
        "self_awareness_index": round(index, 6),
        "meta_layer_K24":       round(meta_layer, 6),
        "terminal_K100":        round(terminal, 6),
        "identity_coherence":   round(identity_coherence, 6),
        "level":                level,
    }



def heisenberg_buffer(P: np.ndarray, confidence: float = 0.8) -> dict:
    """M45 — Uncertainty principle analog (10 blocks of 10).
    dominant_block = argmax(block_means); uncertainty = 1/(confidence*mean+1e-10);
    dogma_risk = confidence * uncertainty; calibrated = 0.5 < dogma_risk < 2.0.
    """
    blocks = P.reshape(10, 10)
    block_means = blocks.mean(axis=1)

    dominant_block = int(np.argmax(block_means))
    uncertainty    = 1.0 / (confidence * float(block_means[dominant_block]) + 1e-10)
    dogma_risk     = confidence * uncertainty
    calibrated     = bool(0.5 < dogma_risk < 2.0)

    return {
        "dominant_block": dominant_block,
        "uncertainty":    round(uncertainty, 6),
        "dogma_risk":     round(dogma_risk, 6),
        "calibrated":     calibrated,
    }



def godel_incompleteness(P: np.ndarray) -> dict:
    """M46 — Gödelian limit: what the persona cannot prove about itself.
    self_reference_score=P[23]; incompleteness_ratio=1-self_awareness_index;
    godel_statement lists below-median blocks; provable_fraction=self_awareness_index.
    """
    self_ref = float(P[23])

    identity_coherence = 1.0 - float(np.std(P))
    awareness = (float(P[23]) + float(P[99])) / 2.0 * identity_coherence
    incompleteness = 1.0 - awareness

    blocks = P.reshape(10, 10)
    block_means = blocks.mean(axis=1)
    # lowest-activation blocks (below median)
    threshold = float(np.median(block_means))
    unknown_blocks = [f"B{i}" for i, m in enumerate(block_means) if m < threshold]
    godel_statement = "The persona cannot fully know: " + ", ".join(unknown_blocks)

    return {
        "self_reference_score":  round(self_ref, 6),
        "incompleteness_ratio":  round(incompleteness, 6),
        "godel_statement":       godel_statement,
        "provable_fraction":     round(awareness, 6),
    }
