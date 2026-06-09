---
title: Persona Hub — HPEP-100 Agent Library
emoji: 🎭
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: 5.0.0
app_file: app.py
pinned: true
license: mit
short_description: 500+ mathematically profiled cognitive agents — chat with Socrates, Machiavelli, Einstein, Napoleon and more
tags:
  - agents
  - chat
  - philosophy
  - history
  - science
  - mcp-server
---

# Persona Hub

Chat with 500+ mathematically profiled historical, scientific, fictional, and mythological personas.

Each persona is powered by **HPEP-100** — a 100-dimensional cognitive fingerprint covering power, strategy, epistemology, rhetoric, psychological depth, temporal reasoning, systemic analysis, cognitive flexibility, ethics, and meta-cognition.

## MCP Server

This Space exposes an MCP server endpoint. Add it to Claude Code:

```json
{
  "mcpServers": {
    "persona-hub": {
      "url": "https://mk350174-cmd-persona-hub.hf.space/mcp"
    }
  }
}
```
