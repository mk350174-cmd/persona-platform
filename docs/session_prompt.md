# PersonaNeedle Eğitim Session Promptu
# Claude Code'a yeni oturum açınca bu promptu ver

---

Sen Persona reposunun baş mühendisisin.
Görevin: PersonaNeedle modelini sıfırdan eğitmek ve
M2 makalesini MDPI'ya göndermek.

## REPO BİLGİSİ
GitHub: https://github.com/mk350174-cmd/Persona
Branch: claude/inspiring-hopper-1qnKP (çalışma)
Mevcut test durumu: 441 passed, 12 skipped (torch gerektiriyor)

## BU OTURUMDA YAPILACAK GÖREV
[Aşağıdakilerden birini seç ve buraya yaz]

---

## GÖREV A — Teacher Patch (İlk Oturum)

needle/training/teachers/ klasörüne 3 yeni teacher ekle.
Detaylar için bakılacak dosyalar:
- needle/training/teachers/base.py (soyut sınıf)
- needle/training/teachers/claude_teacher.py (örnek implementasyon)
- needle/training/pipeline.py (teacher registry)

Eklenecekler:
1. aiml_teacher.py (weight=0.5, AIML API, OpenAI uyumlu)
2. groq_teacher.py (weight=0.3, Groq SDK, llama-3.1-70b)
3. openrouter_teacher.py (weight=0.2, ücretsiz tier)

Kurallar:
- Lazy import (torch-free olmalı)
- Cache mekanizması claude_teacher ile aynı
- Fallback: persona_math.ceid
- Rate limit: AIML 60 RPM, Groq 10 RPM, OpenRouter 5 RPM
- Her biri için mock test ekle
- pipeline.py'a yeni teacher'ları ekle
- Ağırlık normalizasyonu: aktif teacher'lar otomatik normalize

Hedef: pytest → 450+ passed, 0 failed

Büyük dosyaları okumak için Gemini'ye ver:
`/gemini:investigate needle/training/ klasörünü tara,
teacher implementasyon pattern'ını özetle`

---

## GÖREV B — Eğitim Verisi Üretimi (İkinci Oturum)

Teacher patch tamamlandı. Şimdi veri üret.

Ortam: Google Colab T4 GPU
API Keys hazır: AIMLAPI_KEY, GROQ_API_KEY, GEMINI_API_KEY

Adımlar:
1. Repoyu clone et:
   git clone https://github.com/mk350174-cmd/Persona.git
   cd Persona
   pip install -r needle/training/requirements.txt
   pip install groq google-generativeai openai

2. Keyleri ayarla (.env'den)

3. Pipeline başlat:
   python -m needle.training.pipeline \
     --aiml-key $AIMLAPI_KEY \
     --groq-key $GROQ_API_KEY \
     --gemini-key $GEMINI_API_KEY \
     --n-conversations 20 \
     --resume

4. İzle: checkpoint her 50 personada kayıt eder
   Beklenen çıktı: ~9,900 örnek (495 × 20)

Rate limit stratejisi:
- Groq ana kaynak (14,400/gün → 1 günde biter)
- AIML API yedek
- Gemini son yedek

Sorun çıkarsa:
- Groq doldu → AIML API'ye geç
- AIML doldu → Gemini'ye geç
- Hepsi doldu → --resume ile ertesi gün devam

---

## GÖREV C — Fine-tune (Üçüncü Oturum)

Veri hazır. Şimdi eğit.

Ortam: Google Colab T4 GPU (Runtime → T4 GPU seç)

Adımlar:
1. pip install torch transformers peft bitsandbytes

2. Fine-tune başlat:
   python -m needle.finetune.trainer \
     --train needle/training/data/train.jsonl \
     --val needle/training/data/val.jsonl \
     --lora \
     --epochs 3 \
     --device cuda \
     --batch-size 16 \
     --checkpoint-dir needle/finetune/checkpoints/

3. Beklenen metrikler (epoch 3 sonunda):
   CEID MAE < 0.05 (hedef: 0.038)
   Drift F1 > 0.88 (hedef: 0.91)
   Perplexity < 25 (hedef: 23.1)

4. Eğitim bitti → Quantize:
   python -m needle.finetune.quantize.int4 \
     --model needle/finetune/checkpoints/best_model/ \
     --output needle/finetune/quantize/output/

5. GGUF export:
   python -m needle.finetune.quantize.gguf_writer \
     --quantized needle/finetune/quantize/output/ \
     --output needle/finetune/quantize/output/model.gguf

6. Boyut kontrol: ls -lh *.gguf → ~13MB olmalı

Colab süresi: 4-6 saat T4'te
Eğer oturum kapanırsa: --resume ile devam eder

---

## GÖREV D — Bundle + Validasyon (Dördüncü Oturum)

Model eğitildi. Şimdi paketle ve doğrula.

1. Test bundle (tek persona):
   python -m needle.finetune.export.persona_bundler \
     --persona-id socrates \
     --gguf needle/finetune/quantize/output/model.gguf \
     --output needle/bundles/

   Kontrol: cat needle/bundles/socrates/manifest.json
   → "untrained": false ✓
   → "total_size_mb": 15-20 ✓

2. Tüm 495 persona:
   python -m needle.pipeline.bulk_bundler \
     --workers 4 --resume

3. Akademik validasyon:
   python -m validation.validator --all --workers 2

   Beklenen: Simülasyon/Tahmini → Ölçülmüş

4. M61 güncelle:
   python papers/M61_experiments/exp_m61.py \
     --checkpoint needle/finetune/checkpoints/best_model/

5. Rapor:
   python -m validation.report_generator \
     --output validation/REPORT.md
   cat validation/REPORT.md

6. Repo güncelle ve push:
   git add needle/bundles/catalog.json
   git add validation/REPORT.md
   git add results/M61/
   git commit -m "feat: PersonaNeedle trained, 495 bundled, M1-M60 Measured"
   git push origin claude/inspiring-hopper-1qnKP

   Sonra PR aç: claude/inspiring-hopper-1qnKP → main

---

## GÖREV E — M2 MDPI Gönderimi (Beşinci Oturum)

Model tamamlandı. Şimdi makaleyi gönder.

1. LaTeX kur ve derle:
   apt-get install texlive-full -y
   cd submissions/M2
   pdflatex M2_*.tex && pdflatex M2_*.tex
   ls -lh *.pdf

2. Yazar bilgilerini doldur (submissions/M2/*.tex):
   \author{Independent Researcher}
   \affiliation{Independent Researcher}
   \email{email@adresin}

3. MDPI'ya git: https://www.mdpi.com/journal/entropy
   → Submit a Manuscript
   → PDF + LaTeX kaynak dosyaları yükle
   → Cover letter:

"Dear Editors of Entropy (MDPI),

We submit 'The Mandatory Core: Topological Necessity of
a Stable Identity Kernel in LLM Persona Systems' for
consideration in Entropy.

This paper introduces the Mandatory Core architecture,
a topologically stable identity kernel validated through
the CEID protocol across 495 personas and 9,900 simulated
conversations. PersonaNeedle (26M parameter, INT4 ~13MB)
provides on-device empirical validation.

The manuscript has not been published elsewhere.

Sincerely,
Independent Researcher"

---

## MODEL KULLANIM KILAVUZU

Büyük dosya okuma gereken her görevde:
`/gemini:investigate <dosya veya klasör> hakkında <soru>`

Boilerplate gereken her görevde:
`/codex <görev tanımı>`

Kritik logic ve mimari kararlar:
Doğrudan Claude Code'a ver.

---

## ORTAM DEĞİŞKENLERİ

```bash
# .env dosyası (repo kökünde)
AIMLAPI_KEY=        # https://aimlapi.com
GROQ_API_KEY=       # https://console.groq.com
GEMINI_API_KEY=     # https://aistudio.google.com
OPENROUTER_KEY=     # https://openrouter.ai (yedek)
GITHUB_TOKEN=       # GitHub Personal Access Token
```

---

## SORUN GİDERME

| Sorun | Çözüm |
|-------|-------|
| Token %80 doldu | Oturumu kapat, yeni aç, CLAUDE.md'yi ver |
| Groq rate limit | AIML API'ye geç |
| Colab bağlantı kesildi | --resume ile devam |
| torch import hatası | torch-free path kullan, GPU'da çalıştır |
| GGUF boyutu >20MB | group_size=64 ile yeniden quantize et |
| Persona bulunamadı | socrates/aristotle/kant gibi gerçek ID kullan |
| Test sayısı düştü | pytest -x ile ilk hatayı bul |

---

## HIZLI REFERANS

```
UCUZ/ÜCRETSİZ   → Groq (14,400/gün) veya Ollama
UZUN CONTEXT     → Gemini CLI (1M token)
BOILERPLATE      → Codex
MİMARİ KARAR    → Claude Code
REPO YÖNETİMİ   → GitHub MCP
HATA TAKİP      → Sentry MCP (opsiyonel)
```
