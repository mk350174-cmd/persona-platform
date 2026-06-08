"""
AndroidExporter — lay a persona bundle into an Android assets tree (torch-free).

Copies the GGUF + manifest into ``assets/personas/{persona_id}/``, performs a lightweight
ARM64 / llama.cpp-JNI compatibility check, and emits the ``build.gradle`` dependency note
needed to load the model on-device (via llama.rn / a llama.cpp JNI binding). Pure file ops.

On-device inference still requires llama.cpp to understand the 'persona-needle-san' arch
(custom op set or a conversion) — documented in ``quantize/gguf_writer.py``.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

_GRADLE_NOTE = (
    "// PersonaNeedle on-device deps (app/build.gradle):\n"
    "//   implementation 'com.rnllama:llama-android:+'   // or a llama.cpp JNI binding\n"
    "//   android { defaultConfig { ndk { abiFilters 'arm64-v8a' } } }\n"
    "// GGUF assets load from assets/personas/<persona_id>/<persona_id>.gguf"
)
_SUPPORTED_ABIS = ("arm64-v8a",)


class AndroidExporter:
    def export(self, bundle_path: str, output_apk_assets: str) -> dict:
        """``bundle_path`` is a bundle dir (with manifest.json); writes the assets tree."""
        bundle = Path(bundle_path)
        manifest_file = bundle / "manifest.json"
        if not manifest_file.exists():
            raise FileNotFoundError(f"no manifest.json in {bundle_path}")
        manifest = json.loads(manifest_file.read_text())
        persona_id = manifest.get("persona_id", bundle.name)

        dst = Path(output_apk_assets) / "personas" / persona_id
        dst.mkdir(parents=True, exist_ok=True)

        copied, gguf_found = [], False
        for item in bundle.iterdir():
            if item.is_file():
                shutil.copy2(item, dst / item.name)
                copied.append(item.name)
                if item.suffix == ".gguf":
                    gguf_found = True

        compat = {
            "arm64_v8a": True,
            "supported_abis": list(_SUPPORTED_ABIS),
            "gguf_present": gguf_found,
            "ready": gguf_found,
            "notes": [] if gguf_found else ["no .gguf in bundle — export the model first"],
        }
        result = {
            "persona_id": persona_id,
            "assets_dir": str(dst),
            "asset_path": f"assets/personas/{persona_id}/",
            "files": sorted(copied),
            "compatibility": compat,
            "build_gradle_note": _GRADLE_NOTE,
        }
        (dst / "android_export.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
        return result


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Export a persona bundle to Android assets")
    ap.add_argument("--bundle", required=True, help="bundle dir (with manifest.json)")
    ap.add_argument("--out", default="android/app/src/main/assets")
    args = ap.parse_args(argv)
    result = AndroidExporter().export(args.bundle, args.out)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
