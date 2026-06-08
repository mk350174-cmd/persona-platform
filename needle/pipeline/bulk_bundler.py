"""
BulkBundler — build deployable bundles for the whole persona library.

Discovers every persona, fills missing components (GGUF model / visual / audio) with
``PlaceholderFactory`` stand-ins (marking the bundle ``untrained``), and writes a
15–20 MB-target bundle per persona via ``needle.finetune.export.PersonaBundler``. Supports
parallel workers, checkpoint/resume, dry-run, and a catalog over all personas.

Torch-free: untrained bundles use placeholders, so the whole pipeline runs without torch /
the gguf lib / a trained model.

    python -m needle.pipeline.bulk_bundler --output needle/bundles/ --workers 4
    python -m needle.pipeline.bulk_bundler --dry-run
    python -m needle.pipeline.bulk_bundler --catalog-only
"""

from __future__ import annotations

import json
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from needle.finetune.export.persona_bundler import PersonaBundler, default_model_size_mb
from .placeholder_factory import PlaceholderFactory

try:  # optional progress bar
    from tqdm import tqdm
except Exception:  # pragma: no cover
    def tqdm(it, **kw):
        return it

_COMPONENTS = ("model", "visual", "audio")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class BulkBundler:
    def __init__(self, personas_dir: str = "persona_math/personas/",
                 output_dir: str = "needle/bundles/",
                 visual_dir: str = "assets/visuals/",
                 audio_dir: str = "assets/audio/",
                 trained_dir: Optional[str] = None,
                 model_gguf: Optional[str] = None):
        self.personas_dir = Path(personas_dir)
        self.output_dir = Path(output_dir)
        self.visual_dir = Path(visual_dir)
        self.audio_dir = Path(audio_dir)
        self.trained_dir = Path(trained_dir) if trained_dir else None
        # a single fine-tuned GGUF shared by all personas (PersonaNeedle is conditioned
        # per-persona by the K-layer prefix, so one trained model serves every persona)
        self.model_gguf = str(model_gguf) if model_gguf else None
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.bundler = PersonaBundler()
        self.placeholders = PlaceholderFactory(out_dir=self.output_dir / "_placeholders")

    # ── discovery ────────────────────────────────────────────────────────────────
    def _real_assets(self, persona_id: str) -> dict:
        if self.model_gguf and Path(self.model_gguf).exists():
            model = self.model_gguf                       # shared trained model → trained bundle
        else:
            gguf = self.trained_dir / f"{persona_id}.gguf" if self.trained_dir else None
            model = str(gguf) if gguf and gguf.exists() else None
        return {
            "model": model,
            "visual": str(self.visual_dir / f"{persona_id}.png")
            if (self.visual_dir / f"{persona_id}.png").exists() else None,
            "audio": str(self.audio_dir / f"{persona_id}.mp3")
            if (self.audio_dir / f"{persona_id}.mp3").exists() else None,
        }

    def discover_personas(self, limit: Optional[int] = None) -> list[dict]:
        from persona_math.persona_library import PERSONA_LIBRARY
        ids = sorted(PERSONA_LIBRARY)
        if limit is not None:
            ids = ids[:limit]
        out = []
        for pid in ids:
            spec = PERSONA_LIBRARY[pid]
            real = self._real_assets(pid)
            missing = [c for c in _COMPONENTS if real[c] is None]
            out.append({
                "id": pid,
                "domain": spec.get("domain") if isinstance(spec, dict) else None,
                "real_assets": real,
                "missing": missing,
                "untrained": real["model"] is None,   # no trained GGUF ⇒ untrained
            })
        return out

    def _bundle_exists(self, persona_id: str) -> bool:
        return (self.output_dir / persona_id / "manifest.json").exists()

    # ── single bundle ────────────────────────────────────────────────────────────
    def create_bundle(self, persona_id: str, force: bool = False, dry_run: bool = False) -> dict:
        from persona_math.persona_library import get_library_persona, PERSONA_LIBRARY
        real = self._real_assets(persona_id)
        missing = [c for c in _COMPONENTS if real[c] is None]
        untrained = real["model"] is None

        if dry_run:
            return {"persona_id": persona_id, "untrained": untrained, "missing": missing,
                    "dry_run": True, "would_create": force or not self._bundle_exists(persona_id)}
        if self._bundle_exists(persona_id) and not force:
            return {"persona_id": persona_id, "skipped": True, "untrained": untrained}

        with tempfile.TemporaryDirectory() as stage:
            stage = Path(stage)
            # K-layer (always available from the library)
            try:
                kvec = list(map(float, get_library_persona(persona_id)))
            except Exception:
                kvec = []
            klayer_path = stage / f"{persona_id}_klayer.json"
            klayer_path.write_text(json.dumps({"persona_id": persona_id, "k_layer": kvec}))

            gguf = real["model"] or self.placeholders.create_untrained_gguf(persona_id, out_dir=stage)
            visual = real["visual"] or self.placeholders.create_default_visual(persona_id, out_dir=stage)
            audio = real["audio"] or self.placeholders.create_silent_audio(persona_id, out_dir=stage)

            spec = PERSONA_LIBRARY.get(persona_id, {})
            manifest = self.bundler.bundle(
                persona_id, gguf_path=gguf, k_layer_path=str(klayer_path),
                visual_path=visual, audio_path=audio, output_dir=str(self.output_dir),
                ceid_baseline={"domain": spec.get("domain") if isinstance(spec, dict) else None})
        manifest["untrained"] = untrained
        (self.output_dir / persona_id / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2))
        return {"persona_id": persona_id, "size_mb": manifest["total_size_mb"],
                "untrained": untrained, "missing": missing}

    # ── bulk ─────────────────────────────────────────────────────────────────────
    def bundle_all(self, workers: int = 4, resume: bool = True, dry_run: bool = False,
                   limit: Optional[int] = None) -> dict:
        personas = self.discover_personas(limit=limit)
        progress_path = self.output_dir / "bundle_progress.json"
        done = set()
        if resume and progress_path.exists():
            done = set(json.loads(progress_path.read_text()).get("done", []))

        pending = [p for p in personas
                   if not (resume and (p["id"] in done or self._bundle_exists(p["id"])))]
        skipped = len(personas) - len(pending)

        if dry_run:
            return {"total": len(personas), "bundled": 0, "skipped": skipped,
                    "would_bundle": len(pending), "failed": [],
                    "untrained": sum(p["untrained"] for p in pending),
                    "trained": sum(not p["untrained"] for p in pending),
                    "avg_size_mb": None, "dry_run": True}

        results, failed, sizes = [], [], []

        def _work(pid):
            return self.create_bundle(pid)

        with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
            futures = {ex.submit(_work, p["id"]): p["id"] for p in pending}
            for i, fut in enumerate(tqdm(as_completed(futures), total=len(futures), desc="bundling"), 1):
                pid = futures[fut]
                try:
                    res = fut.result()
                    results.append(res)
                    if "size_mb" in res:
                        sizes.append(res["size_mb"])
                    done.add(pid)
                except Exception as exc:        # pragma: no cover
                    failed.append({"persona_id": pid, "error": str(exc)})
                if i % 50 == 0:
                    print(f"[bulk_bundler] {i}/{len(futures)} done ({len(failed)} failed)")
                    progress_path.write_text(json.dumps({"done": sorted(done)}))

        progress_path.write_text(json.dumps({"done": sorted(done)}))
        bundled = [r for r in results if r.get("size_mb") is not None]
        return {
            "total": len(personas), "bundled": len(bundled), "skipped": skipped,
            "failed": failed,
            "untrained": sum(r.get("untrained", True) for r in bundled),
            "trained": sum(not r.get("untrained", True) for r in bundled),
            "avg_size_mb": round(sum(sizes) / len(sizes), 2) if sizes else None,
        }

    # ── catalog ──────────────────────────────────────────────────────────────────
    def generate_catalog(self, limit: Optional[int] = None) -> dict:
        personas = self.discover_personas(limit=limit)
        entries = []
        for p in personas:
            mpath = self.output_dir / p["id"] / "manifest.json"
            if mpath.exists():
                m = json.loads(mpath.read_text())
                size_mb, components = m.get("total_size_mb"), m.get("components", {})
                untrained = m.get("untrained", p["untrained"])
            else:
                size_mb = default_model_size_mb()      # computed INT4 footprint (Hesaplanan)
                components = {c: {"placeholder": c in p["missing"]} for c in _COMPONENTS}
                untrained = p["untrained"]
            entries.append({"id": p["id"], "domain": p["domain"], "size_mb": size_mb,
                            "untrained": untrained, "components": components})
        catalog = {"generated_at": _now(), "total_personas": len(entries), "personas": entries}
        (self.output_dir / "catalog.json").write_text(
            json.dumps(catalog, ensure_ascii=False, indent=2))
        return catalog


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Bulk-bundle the persona library")
    ap.add_argument("--output", default="needle/bundles/")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--gguf", default=None,
                    help="single fine-tuned GGUF shared by all personas (→ trained bundles)")
    ap.add_argument("--trained-dir", default=None, help="dir of per-persona {id}.gguf models")
    ap.add_argument("--trained-only", action="store_true", help="bundle only personas with a trained GGUF")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--catalog-only", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--resume", dest="resume", action="store_true", default=True,
                    help="skip already-built bundles (default)")
    ap.add_argument("--no-resume", dest="resume", action="store_false")
    args = ap.parse_args(argv)

    bb = BulkBundler(output_dir=args.output, trained_dir=args.trained_dir, model_gguf=args.gguf)
    if args.catalog_only:
        cat = bb.generate_catalog(limit=args.limit)
        print(f"catalog: {cat['total_personas']} personas → {args.output}catalog.json")
        return 0
    if args.trained_only and not (args.trained_dir or args.gguf):
        print("[bulk_bundler] --trained-only needs --trained-dir/--gguf; nothing trained → exiting")
        return 0
    stats = bb.bundle_all(workers=args.workers, resume=args.resume, dry_run=args.dry_run,
                          limit=args.limit)
    bb.generate_catalog(limit=args.limit)
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
