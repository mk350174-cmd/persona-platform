"""
HPEP Studio Python SDK
======================
Usage:
    import hpep
    client = hpep.Client(api_key="hpep_...")
    persona = client.personas("ws_id").create(
        name="Strategic Advisor",
        blocks={"B1": 0.9, "B2": 0.85, "B7": 0.8},
    )
    print(persona.ceid_score)
    print(persona.compile("claude", "rich"))
"""

from hpep.client import Client
from hpep.models import Persona, Workspace, CeidDiagnostic

__version__ = "1.0.0"
__all__ = ["Client", "Persona", "Workspace", "CeidDiagnostic"]
