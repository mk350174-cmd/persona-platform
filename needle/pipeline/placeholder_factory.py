"""
PlaceholderFactory — generate stand-in components for personas that aren't trained /
don't have visual or audio assets yet, so the bulk bundler can still produce a complete
(``untrained``) bundle.

All writers are stdlib-only (no torch, no ``gguf`` lib, no Pillow required):
  * a minimal but valid GGUF container (magic + header + a few metadata KV, 0 tensors),
  * a 256×256 gray PNG (Pillow draws the initials if available; else a solid stdlib PNG),
  * a 1-second silent WAV (``wave``).
"""

from __future__ import annotations

import struct
import wave
import zlib
from pathlib import Path
from typing import Optional

# GGUF metadata value types
_GGUF_TYPE_BOOL = 7
_GGUF_TYPE_STRING = 8


def _gguf_string(s: str) -> bytes:
    b = s.encode("utf-8")
    return struct.pack("<Q", len(b)) + b


def _solid_png(path: Path, w: int, h: int, rgb=(136, 136, 136)) -> None:
    """Write a valid solid-colour RGB PNG using only stdlib (zlib)."""
    def chunk(typ: bytes, data: bytes) -> bytes:
        body = typ + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)         # 8-bit, colour type 2 (RGB)
    row = b"\x00" + bytes(rgb) * w                              # filter byte + pixels
    raw = row * h
    idat = zlib.compress(raw, 9)
    path.write_bytes(sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b""))


class PlaceholderFactory:
    def __init__(self, out_dir: str | Path = "needle/bundles/_placeholders"):
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def _dir(self, out_dir: Optional[str | Path]) -> Path:
        d = Path(out_dir) if out_dir else self.out_dir
        d.mkdir(parents=True, exist_ok=True)
        return d

    def create_untrained_gguf(self, persona_id: str, config=None,
                              out_dir: Optional[str | Path] = None) -> str:
        """Minimal valid GGUF (magic + version 3 + 0 tensors + metadata KV incl.
        ``persona.untrained=true``). Symbolic — replaced by the real model once trained."""
        path = self._dir(out_dir) / f"{persona_id}.gguf"
        arch = getattr(config, "quantization", "INT4") if config else "INT4"
        kvs = [
            _gguf_string("general.architecture") + struct.pack("<I", _GGUF_TYPE_STRING)
            + _gguf_string("persona-needle-san"),
            _gguf_string("general.name") + struct.pack("<I", _GGUF_TYPE_STRING)
            + _gguf_string(persona_id),
            _gguf_string("persona.quantization") + struct.pack("<I", _GGUF_TYPE_STRING)
            + _gguf_string(str(arch)),
            _gguf_string("persona.untrained") + struct.pack("<I", _GGUF_TYPE_BOOL)
            + struct.pack("<?", True),
        ]
        header = (b"GGUF" + struct.pack("<I", 3) + struct.pack("<Q", 0)
                  + struct.pack("<Q", len(kvs)) + b"".join(kvs))
        path.write_bytes(header)
        return str(path)

    def create_default_visual(self, persona_id: str,
                              out_dir: Optional[str | Path] = None) -> str:
        """256×256 gray avatar PNG (initials via Pillow if available, else solid)."""
        path = self._dir(out_dir) / f"{persona_id}.png"
        initials = "".join(w[0] for w in persona_id.replace("_", " ").split()[:2]).upper() or "?"
        try:
            from PIL import Image, ImageDraw      # optional
            img = Image.new("RGB", (256, 256), (136, 136, 136))
            d = ImageDraw.Draw(img)
            d.text((110, 118), initials, fill=(240, 240, 240))
            img.save(path)
        except Exception:
            _solid_png(path, 256, 256, (136, 136, 136))
        return str(path)

    def create_silent_audio(self, persona_id: str,
                            out_dir: Optional[str | Path] = None) -> str:
        """1-second silent mono WAV (stdlib ``wave``; named .wav since wave can't emit MP3)."""
        path = self._dir(out_dir) / f"{persona_id}.wav"
        rate = 22050
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(b"\x00\x00" * rate)     # 1 s of silence
        return str(path)
