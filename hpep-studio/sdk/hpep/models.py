"""SDK data models (thin wrappers around API responses)."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CeidDiagnostic:
    c_axis: float
    e_axis: float
    i_axis: float
    d_axis: float
    overall: float
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "CeidDiagnostic":
        return cls(
            c_axis=d.get("c_axis", 0.0),
            e_axis=d.get("e_axis", 0.0),
            i_axis=d.get("i_axis", 0.0),
            d_axis=d.get("d_axis", 0.0),
            overall=d.get("overall", d.get("ceid_score", 0.0)),
            raw=d,
        )

    def __repr__(self):
        return (
            f"CeidDiagnostic(overall={self.overall:.3f}, "
            f"C={self.c_axis:.3f}, E={self.e_axis:.3f}, "
            f"I={self.i_axis:.3f}, D={self.d_axis:.3f})"
        )


@dataclass
class Persona:
    id: str
    name: str
    blocks: dict
    ceid_score: Optional[float]
    version: int
    workspace_id: str
    description: Optional[str] = None
    k_overrides: dict = field(default_factory=dict)
    is_public: bool = False
    _client: object = field(default=None, repr=False)

    @classmethod
    def from_dict(cls, d: dict, client=None) -> "Persona":
        return cls(
            id=d["id"],
            name=d["name"],
            blocks=d.get("blocks", {}),
            ceid_score=d.get("ceid_score"),
            version=d.get("version", 1),
            workspace_id=d.get("workspace_id", ""),
            description=d.get("description"),
            k_overrides=d.get("k_overrides", {}),
            is_public=d.get("is_public", False),
            _client=client,
        )

    def compile(self, platform: str = "claude", tier: str = "standard") -> str:
        """Compile persona to a system prompt for the given platform and tier."""
        if self._client is None:
            raise RuntimeError("Persona not bound to a client.")
        result = self._client._post(
            f"/workspaces/{self.workspace_id}/personas/{self.id}/compile",
            {"platform": platform, "tier": tier},
        )
        return result.get("system_instruction", "")

    def compile_all(self) -> dict:
        """Compile for all platforms and tiers."""
        if self._client is None:
            raise RuntimeError("Persona not bound to a client.")
        return self._client._post(
            f"/workspaces/{self.workspace_id}/personas/{self.id}/compile/all", {}
        )

    def ceid(self) -> CeidDiagnostic:
        """Fetch full 4-axis CEID diagnostic."""
        if self._client is None:
            raise RuntimeError("Persona not bound to a client.")
        data = self._client._get(
            f"/workspaces/{self.workspace_id}/personas/{self.id}/ceid"
        )
        return CeidDiagnostic.from_dict(data)

    def export(self, format: str = "json") -> dict:
        if self._client is None:
            raise RuntimeError("Persona not bound to a client.")
        return self._client._get(
            f"/workspaces/{self.workspace_id}/personas/{self.id}/export",
            params={"format": format},
        )

    def update(self, **kwargs) -> "Persona":
        if self._client is None:
            raise RuntimeError("Persona not bound to a client.")
        data = self._client._put(
            f"/workspaces/{self.workspace_id}/personas/{self.id}", kwargs
        )
        return Persona.from_dict(data, client=self._client)

    def __repr__(self):
        return f"Persona(id={self.id!r}, name={self.name!r}, ceid={self.ceid_score})"


@dataclass
class Workspace:
    id: str
    name: str
    plan_tier: str
    member_count: int
    persona_count: int
    limits: dict = field(default_factory=dict)
    _client: object = field(default=None, repr=False)

    @classmethod
    def from_dict(cls, d: dict, client=None) -> "Workspace":
        return cls(
            id=d["id"],
            name=d["name"],
            plan_tier=d.get("plan_tier", "free"),
            member_count=d.get("member_count", 0),
            persona_count=d.get("persona_count", 0),
            limits=d.get("limits", {}),
            _client=client,
        )

    def __repr__(self):
        return (
            f"Workspace(id={self.id!r}, name={self.name!r}, "
            f"plan={self.plan_tier!r}, personas={self.persona_count})"
        )
