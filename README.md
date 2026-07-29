# Persona Platform

**Persona engineering ecosystem** — K-layer persona math, PersonaNeedle (SAN model),
an MCP server, and 11 ready-to-use historical/fictional persona agents.

[![CI](https://github.com/mk350174-cmd/persona-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/mk350174-cmd/persona-platform/actions)
[![Security Scanning](https://github.com/mk350174-cmd/persona-platform/actions/workflows/security.yml/badge.svg)](https://github.com/mk350174-cmd/persona-platform/actions)

---

## Overview

This repo currently holds the **engineering core** of the Persona ecosystem:

- **`persona_math/`** — K-layer persona vectors, CEID (Composite Epistemic Identity
  Drift) scoring, the persona library and network model
- **`needle/`** — PersonaNeedle: architecture, training-data pipeline, LoRA
  fine-tuning, INT4 quantization, and bulk persona bundling
- **`persona_mcp/`** — an MCP server exposing persona tools (activation, comparison,
  diagnostics, search) plus a memory-tools layer
- **`agents/`** — 11 ready-to-use persona agent definitions (Einstein, Mandela,
  Marie Curie, Napoleon, Machiavelli, Nietzsche, Socrates, Sun Tzu, Tesla, Athena,
  Sherlock Holmes), each carrying an AI-simulation disclosure
- **`legal/`** — Terms of Service / Privacy Policy drafts (⚠️ drafts pending lawyer
  review, not yet in effect)
- **`validation/`** — tier-promotion tracking (Simülasyon → Ölçülmüş discipline)
- **`docs/`** — session prompts, integration guides, prevention rules

**Not in this repo (removed, to be rebuilt separately):** the web/app layer —
REST API, frontend, mobile client, and their deployment/ops tooling (Docker,
nginx, alembic migrations, staging/canary pipelines, load testing). That layer
existed here previously but was torn down as unmaintained scaffolding; it will
be rebuilt from scratch as a separate effort rather than patched in place.

---

## Quick Start

```bash
git clone https://github.com/mk350174-cmd/persona-platform.git
cd persona-platform

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
pip install -e .
```

```python
from persona_math.persona_library import PERSONA_LIBRARY
from persona_math.ceid import ceid_score

# list personas, compute a CEID score, etc. — see persona_math/ for the API
```

MCP server (`persona_mcp/`) is registered via `.mcp.json` — see that file's
`mcpServers` entries for the active MCP integrations (github, memory, context7,
filesystem, plus persona-mcp itself).

---

## Testing

```bash
pytest needle/training/tests -v
pytest persona_mcp/tests -v
```

CI (`.github/workflows/ci.yml`) runs both suites plus `ruff` over
`persona_math/`, `needle/`, `persona_mcp/`. `.github/workflows/security.yml`
runs gitleaks (secrets), bandit (SAST), and trivy (dependency/filesystem scan).

---

## Project Structure

```
persona-platform/
├── persona_math/     K-layer vectors, CEID scoring, persona library, network model
├── needle/           PersonaNeedle: architecture / training / finetune / pipeline
├── persona_mcp/      MCP server (persona tools + memory tools)
├── agents/           11 persona agent definitions (with AI-simulation disclosure)
├── legal/            ToS / Privacy Policy drafts (pending lawyer review)
├── validation/       Tier-promotion tracking (Simülasyon → Ölçülmüş)
├── docs/             Session prompts, integration guides, prevention rules
├── android/          Kotlin runtime
├── data/, notebooks/ Training data + Kaggle/Colab notebooks
├── scripts/          Standalone utility scripts (docx parsing, translation, etc.)
└── requirements.txt  Core dependencies (persona_math/needle/persona_mcp)
```

---

## Security

- **gitleaks** — secret scanning on every push/PR + daily schedule
- **bandit** — Python SAST over `persona_math/`, `needle/`, `persona_mcp/`
- **trivy** — filesystem/dependency vulnerability scan

There is currently no live API, database, or payment surface in this repo — the
security posture described in earlier drafts of this README (auth, rate
limiting, Stripe, GDPR/KVKK soft-delete, etc.) belonged to the removed web/app
layer and will be re-documented once that layer is rebuilt.

---

## Contributing

1. **Branch naming:** `feature/*`, `bugfix/*`, `claude/*`
2. **Commit format:** `type(scope): description`
3. **Tests:** run `pytest needle/training/tests persona_mcp/tests` before committing
4. **Publication-integrity rules:** see `CLAUDE.md` — every tier claim
   (Ölçülmüş/Hesaplanan/Simülasyon/Tahmini) must be labeled, no exceptions

**See [CLAUDE.md](CLAUDE.md)** for the full working principles (torch-free
imports, honest tiering, MCP server list) and **[AUDIT_FINDINGS.md](https://github.com/mk350174-cmd/Persona/blob/main/AUDIT_FINDINGS.md)**
(in the sibling `Persona` repo) for the canonical audit/fix registry covering
both repos.

---

## License

Proprietary. © 2026 Persona Platform. All rights reserved.
