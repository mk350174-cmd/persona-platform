# .claude/skills — Kurulu Skill Seti

Kurulum tarihi: 2026-07-29 · Kaynaklar `/home/user/vendor/` altına klonlandı (repoya commit edilmez).

## Kurulanlar (30)

| Kaynak | Skill'ler |
|---|---|
| `anthropics/skills` | `webapp-testing`, `frontend-design` |
| `mattpocock/skills` — engineering | `research`, `wayfinder`, `improve-codebase-architecture`, `codebase-design`, `domain-modeling`, `diagnosing-bugs`, `tdd`, `code-review`, `implement`, `to-spec`, `to-tickets`, `triage`, `resolving-merge-conflicts`, `prototype`, `grill-with-docs` |
| `mattpocock/skills` — productivity | `grill-me`, `grilling`, `handoff`, `teach`, `writing-great-skills` |
| `mattpocock/skills` — misc | `git-guardrails-claude-code`, `setup-pre-commit` |
| `ComposioHQ/awesome-claude-skills` | `content-research-writer`, `changelog-generator` |
| Persona (yerel) | `persona-activate`, `persona-compare`, `persona-diagnostic`, `persona-search` |

## Bilinçli Olarak Kurulmayanlar

**`anthropics/skills` — 16 skill atlandı.** `docx`, `pdf`, `pptx`, `xlsx`, `canvas-design`,
`mcp-builder`, `skill-creator`, `algorithmic-art`, `internal-comms`, `brand-guidelines`,
`claude-api`, `theme-factory`, `doc-coauthoring`, `web-artifacts-builder`,
`slack-gif-creator` bu ortamda **zaten yerleşik olarak mevcut** — kopyalamak çakışma
yaratır ve context tüketir.

**`ComposioHQ/awesome-claude-skills` — 862/864 atlandı.** Bunların **832'si**
`composio-skills/*-automation` altındaki API stub'ları (brex, ynab, kickbox, nasa,
sendbird, tomba…). Persona mühendisliğiyle ilgisi yok ve `CLAUDE.md`'deki token
tasarrufu kuralına doğrudan aykırı. Üst seviyedeki geri kalanlar (raffle-winner-picker,
invoice-organizer, twitter-algorithm-optimizer, tailored-resume-generator vb.) da
araştırma iş akışına dokunmuyor.

**`mattpocock/skills` — `deprecated/`, `in-progress/`, `personal/` atlandı.** Ayrıca
`ask-matt` ve `setup-matt-pocock-skills` (yazarına özel), `migrate-to-shoehorn` ve
`scaffold-exercises` (Matt'in kendi projelerine özel).

İhtiyaç duyulursa kaynak klonlar `/home/user/vendor/` altında duruyor; tek komutla
ek skill kopyalanabilir.
