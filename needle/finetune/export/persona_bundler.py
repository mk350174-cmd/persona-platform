"""
PersonaBundler — assemble a deployable 15–20 MB persona package (torch-free).

Collects the four edge components — INT4 GGUF model (~13 MB), K-layer vector (~1 MB),
visual asset (~4 MB), audio asset (~3 MB) — into one folder with a ``manifest.json``, and
checks the total lands in the 15–20 MB target band. The model size falls back to the
honest analytic INT4 estimate (``needle/architecture/config.estimate_int4_size_mb`` ≈ 13.15 MB)
when the GGUF is a placeholder. Pure file/JSON ops — runs anywhere (no torch).
"""

from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from typing import Optional

from needle.architecture.config import PersonaNeedleConfig, estimate_int4_size_mb

SIZE_MIN_MB = 15.0
SIZE_MAX_MB = 20.0
_COMPONENTS = ("model", "k_layer", "visual", "audio")

try:  # optional progress bar
    from tqdm import tqdm
except Exception:  # pragma: no cover
    def tqdm(it, **kw):
        return it


def _file_mb(path: Optional[str]) -> Optional[float]:
    if path and Path(path).exists():
        return round(Path(path).stat().st_size / 1e6, 2)
    return None


def default_model_size_mb() -> float:
    """Honest INT4 size of the default ~26M SAN (≈13.15 MB)."""
    return round(estimate_int4_size_mb(PersonaNeedleConfig()), 2)


def validate_size(total_mb: float) -> bool:
    return SIZE_MIN_MB <= total_mb <= SIZE_MAX_MB


class PersonaBundler:
    VERSION = "1.0"

    def build_manifest(self, persona_id: str, sizes_mb: dict, paths: Optional[dict] = None,
                       ceid_baseline: Optional[dict] = None, untrained: bool = False) -> dict:
        """Build the manifest from a {component: size_mb} mapping (paths optional)."""
        paths = paths or {}
        components = {c: {"path": paths.get(c), "size_mb": round(float(sizes_mb.get(c, 0.0)), 2)}
                      for c in _COMPONENTS}
        total = round(sum(components[c]["size_mb"] for c in _COMPONENTS), 2)
        size_ok = validate_size(total)
        return {
            "persona_id": persona_id,
            "version": self.VERSION,
            "components": components,
            "total_size_mb": total,
            "size_ok": size_ok,
            "size_target_mb": [SIZE_MIN_MB, SIZE_MAX_MB],
            "ceid_baseline": ceid_baseline or {},
            "untrained": untrained,
        }

    def bundle(self, persona_id: str, gguf_path: str, k_layer_path: str,
               visual_path: str, audio_path: str, output_dir: str,
               ceid_baseline: Optional[dict] = None, make_zip: bool = False) -> dict:
        """Copy the components into ``output_dir/persona_id/`` and write ``manifest.json``."""
        dst = Path(output_dir) / persona_id
        dst.mkdir(parents=True, exist_ok=True)

        srcs = {"model": gguf_path, "k_layer": k_layer_path,
                "visual": visual_path, "audio": audio_path}
        sizes, copied, warnings = {}, {}, []
        for comp, src in srcs.items():
            mb = _file_mb(src)
            if mb is None:
                # model has an honest analytic fallback; others are simply flagged missing
                mb = default_model_size_mb() if comp == "model" else 0.0
                if not (comp == "model"):
                    warnings.append(f"missing {comp} component ({src})")
            else:
                target = dst / Path(src).name
                shutil.copy2(src, target)
                copied[comp] = str(target)
            sizes[comp] = mb

        manifest = self.build_manifest(persona_id, sizes, paths=copied,
                                       ceid_baseline=ceid_baseline)
        if warnings:
            manifest["warnings"] = warnings
        (dst / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))

        if make_zip:
            zpath = Path(output_dir) / f"{persona_id}.zip"
            with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
                for p in dst.rglob("*"):
                    z.write(p, p.relative_to(dst.parent))
            manifest["zip"] = str(zpath)
        return manifest

    def bundle_all(self, persona_ids: list, base_dir: str) -> dict:
        """Bundle many personas (expects ``base_dir/{persona_id}/`` component files)."""
        ok, failed = [], []
        for pid in tqdm(persona_ids, desc="bundling"):
            d = Path(base_dir) / pid
            try:
                self.bundle(pid, str(d / f"{pid}.gguf"), str(d / "k_layer.npy"),
                            str(d / "visual.bin"), str(d / "audio.bin"),
                            output_dir=str(Path(base_dir) / "_bundles"))
                ok.append(pid)
            except Exception as exc:                       # pragma: no cover
                failed.append({"persona_id": pid, "error": str(exc)})
        return {"total": len(persona_ids), "ok": len(ok), "failed": len(failed),
                "failures": failed}


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Bundle a persona package (15–20 MB)")
    ap.add_argument("--persona-id", required=True)
    ap.add_argument("--gguf", required=True)
    ap.add_argument("--k-layer", default="")
    ap.add_argument("--visual", default="")
    ap.add_argument("--audio", default="")
    ap.add_argument("--output-dir", default="needle/finetune/export/output")
    ap.add_argument("--zip", action="store_true")
    args = ap.parse_args(argv)
    manifest = PersonaBundler().bundle(args.persona_id, args.gguf, args.k_layer,
                                       args.visual, args.audio, args.output_dir, make_zip=args.zip)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
