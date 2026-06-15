#!/usr/bin/env python3
"""
Parse KOMB_NASYON.docx and extract all 250+ hybrid persona combinations.

Output: data/hybrid_personas_raw.jsonl (one JSON per line)
"""

import json
import re
from pathlib import Path
from typing import Optional, Dict, List, Any
from docx import Document


def parse_active_layers(text: str) -> List[int]:
    """Extract K-layer numbers from 'Katman X' references in a paragraph."""
    pattern = r'Katman\s+(\d+)'
    matches = re.findall(pattern, text)

    layers = []
    for match in matches:
        layer_num = int(match)
        if 1 <= layer_num <= 98 and layer_num not in layers:
            layers.append(layer_num)

    return sorted(list(set(layers)))


def extract_all_personas(docx_path: str) -> List[Dict[str, Any]]:
    """Extract all persona combinations from DOCX file."""
    doc = Document(docx_path)

    personas = []
    i = 0
    while i < len(doc.paragraphs):
        para_text = doc.paragraphs[i].text.strip()

        if para_text.startswith("KOMBİNASYON"):
            match = re.match(r'KOMBİNASYON\s+(\d+):\s*(.+?)\s*\((.+?)\)', para_text)
            if not match:
                i += 1
                continue

            combo_num = int(match.group(1))
            name_tr = match.group(2).strip()
            name_en = match.group(3).strip()

            combo = {
                "id": f"komb_{combo_num:03d}_{name_en.lower().replace(' ', '_').replace('-', '_')}",
                "number": combo_num,
                "name_tr": name_tr,
                "name_en": name_en,
                "use_case": "",
                "active_layers": [],
                "suppressed_layers": [],
                "characteristic": "",
            }

            i += 1
            while i < len(doc.paragraphs):
                para = doc.paragraphs[i].text.strip()

                if para.startswith("KOMBİNASYON"):
                    break

                if "Kullanım Amacı:" in para:
                    combo["use_case"] = para.replace("Kullanım Amacı:", "").strip()
                elif "Aktif (Baskın) Katmanlar:" in para:
                    i += 1
                    while i < len(doc.paragraphs):
                        active_para = doc.paragraphs[i].text.strip()
                        if "Baskılanan Katmanlar:" in active_para:
                            combo["suppressed_layers"].extend(parse_active_layers(active_para))
                            break
                        if "Profil Karakteristiği:" in active_para:
                            break
                        if active_para:
                            combo["active_layers"].extend(parse_active_layers(active_para))
                        i += 1
                    continue
                elif "Baskılanan Katmanlar:" in para:
                    combo["suppressed_layers"].extend(parse_active_layers(para))
                elif "Profil Karakteristiği:" in para:
                    combo["characteristic"] = para.replace("Profil Karakteristiği:", "").strip()
                    i += 1
                    while i < len(doc.paragraphs):
                        char_para = doc.paragraphs[i].text.strip()
                        if char_para.startswith("KOMBİNASYON"):
                            break
                        if char_para:
                            combo["characteristic"] += " " + char_para
                        i += 1
                    i -= 1

                i += 1

            combo["active_layers"] = sorted(list(set(combo["active_layers"])))
            combo["suppressed_layers"] = sorted(list(set(combo["suppressed_layers"])))

            if combo["name_tr"] and combo["number"]:
                personas.append(combo)
        else:
            i += 1

    return sorted(personas, key=lambda x: x["number"])


def main():
    docx_path = "/root/.claude/uploads/7f6e0378-449d-56f4-993d-b0f5a288ff2f/3257e9d9-KOMB_NASYON_1_Saf_Rasyonalist_The_Cartesian_Analyst.docx"
    output_dir = Path("/home/user/persona-platform/data")
    output_dir.mkdir(parents=True, exist_ok=True)

    personas = extract_all_personas(docx_path)

    # Write to JSONL
    output_file = output_dir / "hybrid_personas_raw.jsonl"
    with open(output_file, 'w', encoding='utf-8') as f:
        for p in personas:
            f.write(json.dumps(p, ensure_ascii=False) + '\n')

    print(f"✅ Extracted {len(personas)} personas")


if __name__ == "__main__":
    main()
