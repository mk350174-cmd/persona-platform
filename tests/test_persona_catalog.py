from api.persona_catalog import CATALOG, K_LAYER_KEY_MAP


def test_catalog_has_eleven_personas():
    assert len(CATALOG) == 11


def test_machiavelli_has_no_k_layer_vector():
    """Confirmed absent from the 495-persona library, not just unmapped."""
    entry = CATALOG["machiavelli"]
    assert entry.k_layer_available is False
    assert K_LAYER_KEY_MAP["machiavelli"] is None


def test_mapped_personas_report_available():
    for persona_id, k_key in K_LAYER_KEY_MAP.items():
        if k_key is not None:
            assert CATALOG[persona_id].k_layer_available is True


def test_all_entries_have_required_fields():
    for entry in CATALOG.values():
        assert entry.persona_id
        assert entry.name
        assert entry.model
