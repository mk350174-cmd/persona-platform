"""
Unit tests for api/catalog.py — persona vector factories + catalog listing.

Pure (numpy only). Exercising get_persona_vector for each built-in persona runs
the per-persona factory functions (Kant/Holmes/Nietzsche/Sun Tzu/Machiavelli).
"""

import numpy as np
import pytest

from api.catalog import (
    PERSONA_VECTORS, get_persona_vector, list_personas,
)


@pytest.mark.parametrize("pid", ["machiavelli", "kant", "holmes", "nietzsche", "sun_tzu"])
def test_get_persona_vector_shapes(pid):
    v = np.asarray(get_persona_vector(pid), dtype=float)
    assert v.shape == (100,)
    assert np.all((v >= 0.0) & (v <= 1.0))
    assert not np.any(np.isnan(v))


def test_get_persona_vector_unknown_raises():
    with pytest.raises(KeyError):
        get_persona_vector("definitely_unknown")


def test_persona_vectors_registry():
    assert set(PERSONA_VECTORS) >= {"machiavelli", "kant", "holmes", "nietzsche", "sun_tzu"}


def test_list_personas_includes_extended_catalog():
    personas = list_personas()
    ids = {p["id"] for p in personas}
    assert {"kant", "holmes", "nietzsche", "sun_tzu"} <= ids
    for p in personas:
        assert set(p) >= {"id", "name", "label", "price_usd", "ceid_certified"}


def test_kant_is_high_ethics_low_deception():
    v = np.asarray(get_persona_vector("kant"), dtype=float)
    ethics = float(np.mean(v[80:90]))   # Block 9
    deception = v[6]                     # K7
    assert ethics > deception
