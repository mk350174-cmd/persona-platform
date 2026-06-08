"""
build_manifest — generate papers/manifest.json + papers/INDEX.md for all 60
papers (single source of truth for status / version / cross-refs).

M1–M10 are marked ``published`` (finalized in-repo, results embedded); M11–M60
remain ``draft``. "published" here means *finalized in this repository* — NOT
submitted to a journal or arXiv (that is an external, manual step, recorded as
``external_submission``).

    python -m experiments.build_manifest
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_PAPERS = _REPO / "papers"
_RESULTS = _REPO / "results"

FINALIZED = {f"M{i}" for i in range(1, 61)}
EXPERIMENT_MODULE = {
    "M1": "experiments/exp_m1_metallic.py",
    "M2": "experiments/exp_m2_mandatory_core.py",
    "M3": "experiments/exp_m3_ceid_protocol.py",
    "M4": "experiments/exp_m4_court.py",
    "M5": "experiments/exp_m5_kimera_tensor.py",
    "M6": "experiments/exp_m6_arkhe.py",
    "M7": "experiments/exp_m7_tool_table.py",
    "M8": "experiments/exp_m8_hpep_convergent.py",
    "M9": "experiments/exp_m9_ppep_proxy.py",
    "M10": "experiments/exp_m10_atlas.py",
    "M11": "experiments/exp_m11_hegesias.py",
    "M12": "experiments/exp_m12_researcher.py",
    "M13": "experiments/exp_m13_digital_copy.py",
    "M14": "experiments/exp_m14_consent.py",
    "M15": "experiments/exp_m15_soul_test.py",
    "M16": "experiments/exp_m16_d1_multi.py",
    "M17": "experiments/exp_m17_polymathy.py",
    "M18": "experiments/exp_m18_amcc.py",
    "M19": "experiments/exp_m19_rock_river.py",
    "M20": "experiments/exp_m20_termination.py",
    "M21": "experiments/exp_m21_meta_awareness.py",
    "M22": "experiments/exp_m22_synchrony.py",
    "M23": "experiments/exp_m23_hegesias_history.py",
    "M24": "experiments/exp_m24_vine_tree.py",
    "M25": "experiments/exp_m25_poetic_method.py",
    "M26": "experiments/exp_m26_institutional.py",
    "M27": "experiments/exp_m27_organizational.py",
    "M28": "experiments/exp_m28_empathy.py",
    "M29": "experiments/exp_m29_faction.py",
    "M30": "experiments/exp_m30_clinical_drift.py",
    "M31": "experiments/exp_m31_ceid_validation.py",
    "M32": "experiments/exp_m32_hpep_short.py",
    "M33": "experiments/exp_m33_crosslingual.py",
    "M34": "experiments/exp_m34_chimera5.py",
    "M35": "experiments/exp_m35_arch_atlas.py",
    "M36": "experiments/exp_m36_hallucination.py",
    "M37": "experiments/exp_m37_dsuite.py",
    "M38": "experiments/exp_m38_distributed.py",
    "M39": "experiments/exp_m39_conflict.py",
    "M40": "experiments/exp_m40_finetuning.py",
    "M41": "experiments/exp_m41_ptsd.py",
    "M42": "experiments/exp_m42_adolescent_arkhe.py",
    "M43": "experiments/exp_m43_wisdom.py",
    "M44": "experiments/exp_m44_narcissism.py",
    "M45": "experiments/exp_m45_ego_dissolution.py",
    "M46": "experiments/exp_m46_addiction.py",
    "M47": "experiments/exp_m47_parenting.py",
    "M48": "experiments/exp_m48_musician.py",
    "M49": "experiments/exp_m49_character_residue.py",
    "M50": "experiments/exp_m50_author_voice.py",
    "M51": "experiments/exp_m51_cinema.py",
    "M52": "experiments/exp_m52_artist_block.py",
    "M53": "experiments/exp_m53_authoritarian.py",
    "M54": "experiments/exp_m54_ai_safety.py",
    "M55": "experiments/exp_m55_education.py",
    "M56": "experiments/exp_m56_collective_trauma.py",
    "M57": "experiments/exp_m57_climate.py",
    "M58": "experiments/exp_m58_free_will.py",
    "M59": "experiments/exp_m59_consciousness.py",
    "M60": "experiments/exp_m60_mortality.py",
    "M61": "papers/M61_experiments/exp_m61.py",
}

_ID_RE = re.compile(r"^(M\d+)_")
_TARGET_RE = re.compile(r"%\s*(?:Target(?:\s*Journal)?|Hedef)\s*:\s*(.+)")
_DATE_RE = re.compile(r"\\date\{([^}]*)\}")
_VERSION_RE = re.compile(r"[Vv]ersion\s*([0-9.]+)|_v([0-9.]+)")
_CITE_RE = re.compile(r"ManuscriptM(\d+)")


def _paper_id(name: str) -> str | None:
    m = _ID_RE.match(name)
    return m.group(1) if m else None


def _title(text: str, name: str) -> str:
    m = re.search(r"\\title\{(.+?)\n?\}", text, re.DOTALL)
    if m:
        t = m.group(1)
        t = re.sub(r"\\[a-zA-Z]+\*?\{", "", t)   # strip \textbf{ \Large{ etc.
        t = t.replace("{", "").replace("}", "")
        t = re.sub(r"\\[a-zA-Z]+\*?", "", t)     # strip bare \commands
        t = re.sub(r"\\\\|\s+", " ", t).strip()
        if t:
            return t[:200]
    # fall back to the header comment after "% M<n>:" or "% Title:"
    for line in text.splitlines()[:12]:
        m2 = re.search(r"%\s*(?:Title|M\d+)\s*:\s*(.+)", line)
        if m2 and m2.group(1).strip():
            return m2.group(1).strip()[:200]
    return name.replace("_", " ")


def _journal(text: str) -> str:
    m = _TARGET_RE.search(text)
    return m.group(1).strip() if m else "unspecified"


def _version(text: str, name: str) -> str:
    md = _DATE_RE.search(text)
    if md:
        mv = _VERSION_RE.search(md.group(1))
        if mv:
            return (mv.group(1) or mv.group(2))
    mv = re.search(r"_v([0-9.]+)\.tex", name)
    return mv.group(1) if mv else "?"


def _value_tiers(pid: str) -> list[str]:
    rj = _RESULTS / pid / "results.json"
    if not rj.exists():
        return []
    tiers = set()
    data = json.loads(rj.read_text(encoding="utf-8"))

    def walk(o):
        if isinstance(o, dict):
            if "tier" in o and "framework_version" in o:
                tiers.add(o["tier"])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(data)
    return sorted(tiers)


def build() -> dict:
    papers = []
    for path in sorted(_PAPERS.glob("M*"), key=lambda p: int(_paper_id(p.name)[1:])
                       if _paper_id(p.name) else 999):
        if path.suffix not in {".tex", ".txt"}:
            continue
        pid = _paper_id(path.name)
        if not pid:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        refs = sorted({f"M{n}" for n in _CITE_RE.findall(text)} - {pid},
                      key=lambda s: int(s[1:]))
        finalized = pid in FINALIZED
        papers.append({
            "id": pid,
            "file": path.name,
            "title": _title(text, path.name),
            "journal_target": _journal(text),
            "version": _version(text, path.name),
            "status": "published" if finalized else "draft",
            "results_embedded": finalized,
            "results_dir": f"../results/{pid}" if finalized else None,
            "experiment_module": EXPERIMENT_MODULE.get(pid),
            "value_tiers_present": _value_tiers(pid),
            "external_submission": "pending (manual)" if finalized else "n/a",
            "cross_refs": refs,
            "tex_ext": path.suffix,
        })

    manifest = {
        "schema_version": "1.0",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "series": "Persona Engineering Research Series (M1-M61)",
        "status_legend": {
            "published": "finalized in-repo; results embedded; NOT journal/arXiv-submitted",
            "draft": "not yet finalized (author-owned, out of current scope)",
        },
        "n_papers": len(papers),
        "n_published": sum(p["status"] == "published" for p in papers),
        "papers": papers,
    }
    return manifest


def _mermaid(papers: list[dict]) -> str:
    """Cross-reference graph among the finalized M1–M10 set (readability)."""
    fin = {p["id"] for p in papers if p["status"] == "published"}
    lines = ["```mermaid", "graph LR"]
    seen = set()
    for p in papers:
        if p["id"] not in fin:
            continue
        for r in p["cross_refs"]:
            if r in fin and (p["id"], r) not in seen:
                seen.add((p["id"], r))
                lines.append(f"  {p['id']} --> {r}")
    lines.append("```")
    return "\n".join(lines)


def write_index(manifest: dict) -> Path:
    papers = manifest["papers"]
    lines = [
        "# Persona Engineering Research Series — Paper Index",
        "",
        f"_Generated {manifest['generated_utc']} by `experiments/build_manifest.py`._",
        "",
        "> **Note on \"published\":** here it means **finalized in this repository** "
        "(draft markers removed, simulation results embedded). It does **NOT** mean "
        "submitted to or accepted by a journal/arXiv — that is a separate, manual step "
        "(`external_submission: pending`).",
        "> **Figures are data-only:** results are pgfplots `.dat` files under "
        "`results/M*/figdata/` with `\\input`-able `.tex` snippets under `results/M*/tex/`. "
        "PDFs are not built here; compile each paper from the `papers/` directory.",
        "> **Integrity:** every embedded number is tier-stamped "
        "(`Simülasyon`/`Hesaplanan`/`Tahmini`); none is real-LLM `Ölçülmüş` data.",
        "",
        f"**{manifest['n_published']}/{manifest['n_papers']}** papers finalized (M1–M10). "
        "Regenerate results with `make experiments`; rebuild this index with "
        "`python -m experiments.build_manifest`.",
        "",
        "## Status table",
        "",
        "| ID | Title | Journal target | Version | Status | Results | Tiers |",
        "|----|-------|----------------|---------|--------|---------|-------|",
    ]
    for p in papers:
        title = p["title"].replace("|", "\\|")[:60]
        tiers = ", ".join(p["value_tiers_present"]) or "—"
        emb = "✓" if p["results_embedded"] else "—"
        lines.append(f"| {p['id']} | {title} | {p['journal_target'][:32]} | "
                     f"{p['version']} | {p['status']} | {emb} | {tiers} |")
    lines += [
        "",
        "## Cross-reference graph (finalized M1–M10)",
        "",
        "_Edges = `\\cite{ManuscriptM…}` references among finalized papers. "
        "Full adjacency for all 60 is in `manifest.json`._",
        "",
        _mermaid(papers),
        "",
    ]
    out = _PAPERS / "INDEX.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main() -> int:
    manifest = build()
    mpath = _PAPERS / "manifest.json"
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8")
    ipath = write_index(manifest)
    print(f"wrote {mpath.relative_to(_REPO)} ({manifest['n_papers']} papers, "
          f"{manifest['n_published']} published)")
    print(f"wrote {ipath.relative_to(_REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
