"""HPEP Studio SDK — HTTP client."""

import httpx
from typing import Optional

from hpep.models import Persona, Workspace


class PersonaResource:
    def __init__(self, client: "Client", workspace_id: str):
        self._client = client
        self._workspace_id = workspace_id
        self._prefix = f"/workspaces/{workspace_id}/personas"

    def list(self) -> list[Persona]:
        data = self._client._get(self._prefix)
        return [Persona.from_dict(p, client=self._client) for p in data.get("personas", [])]

    def get(self, persona_id: str) -> Persona:
        data = self._client._get(f"{self._prefix}/{persona_id}")
        return Persona.from_dict(data, client=self._client)

    def create(
        self,
        name: str,
        blocks: Optional[dict] = None,
        k_overrides: Optional[dict] = None,
        description: Optional[str] = None,
        is_public: bool = False,
    ) -> Persona:
        """
        Create a custom persona from block specs.

        blocks: dict with B1-B10 keys, e.g. {"B1": 0.9, "B3": 0.7}
                Missing blocks default to 0.5.
        k_overrides: dict with K0-K99 keys for fine-grained control.
        """
        # Normalize block keys
        normalized_blocks = {}
        if blocks:
            for k, v in blocks.items():
                key = k if k.startswith("B") else f"B{k}"
                normalized_blocks[key] = float(v)

        body = {
            "name": name,
            "blocks": normalized_blocks or {},
            "is_public": is_public,
        }
        if description:
            body["description"] = description
        if k_overrides:
            body["k_overrides"] = {str(k): float(v) for k, v in k_overrides.items()}

        data = self._client._post(self._prefix, body)
        return Persona.from_dict(data, client=self._client)

    def import_from_library(self, library_id: str) -> Persona:
        data = self._client._post(
            f"/workspaces/{self._workspace_id}/personas/import/{library_id}", {}
        )
        # Fetch the full persona
        return self.get(data["persona_id"])

    def delete(self, persona_id: str) -> None:
        self._client._delete(f"{self._prefix}/{persona_id}")


class WorkspaceResource:
    def __init__(self, client: "Client"):
        self._client = client

    def list(self) -> list[Workspace]:
        data = self._client._get("/workspaces")
        return [Workspace.from_dict(w, client=self._client) for w in data.get("workspaces", [])]

    def get(self, workspace_id: str) -> Workspace:
        data = self._client._get(f"/workspaces/{workspace_id}")
        return Workspace.from_dict(data, client=self._client)

    def create(self, name: str) -> Workspace:
        data = self._client._post("/workspaces", {"name": name})
        return Workspace.from_dict(data, client=self._client)


class Client:
    """
    HPEP Studio API client.

    Example::

        import hpep

        client = hpep.Client(api_key="hpep_...")

        # Create a persona in your default workspace
        ws = client.workspaces.list()[0]
        persona = client.personas(ws.id).create(
            name="Strategic Thinker",
            blocks={"B1": 0.9, "B2": 0.85, "B7": 0.8},
        )
        print(persona.ceid_score)   # e.g. 0.91
        print(persona.compile("claude", "rich"))
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.hpep.studio",
        timeout: float = 30.0,
    ):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._http = httpx.Client(
            base_url=self._base_url,
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            timeout=timeout,
        )
        self.workspaces = WorkspaceResource(self)

    def personas(self, workspace_id: str) -> PersonaResource:
        return PersonaResource(self, workspace_id)

    def health(self) -> dict:
        return self._get("/health")

    # ── HTTP primitives ───────────────────────────────────────────────────────

    def _get(self, path: str, params: dict = None) -> dict:
        r = self._http.get(path, params=params)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, body: dict) -> dict:
        r = self._http.post(path, json=body)
        r.raise_for_status()
        return r.json()

    def _put(self, path: str, body: dict) -> dict:
        r = self._http.put(path, json=body)
        r.raise_for_status()
        return r.json()

    def _delete(self, path: str) -> None:
        r = self._http.delete(path)
        r.raise_for_status()

    def __repr__(self):
        return f"hpep.Client(base_url={self._base_url!r})"
