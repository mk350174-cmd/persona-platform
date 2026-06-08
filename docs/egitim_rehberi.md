# PersonaNeedle Eğitim Rehberi
## Sıfırdan Eğitilmiş Modele — Adım Adım

---

## 1. ÜCRETSİZ API SEÇENEKLERİ

### Seçenek A — AIML API (EN İYİ SEÇENEK)
- **Limit:** 400+ model, ücretsiz başlangıç kredisi
- **Maliyet:** $0 (kredi kartı gerekmez)
- **Özellik:** Tek key ile Claude, GPT, Gemini, DeepSeek, Llama hepsine erişim
- **PersonaNeedle için:** Tüm 3 öğretmen modeli tek yerden
- **Nasıl alınır:**
  1. https://aimlapi.com adresine git
  2. "Get API Key" → Kayıt ol (Google ile giriş yap)
  3. Ücretsiz kredi otomatik yüklenir
  4. `AIMLAPI_KEY` olarak kaydet

### Seçenek B — OpenRouter (500+ Model, Ücretsiz Tier)
- **Limit:** Ücretsiz modeller sınırsız, premium modeller kredi ile
- **Maliyet:** $0 (ücretsiz modeller için)
- **Özellik:** OpenAI uyumlu API, 500+ model tek endpointten
- **Nasıl alınır:**
  1. https://openrouter.ai adresine git
  2. "Sign In" → Kayıt ol
  3. Keys → Create Key
  4. `OPENROUTER_KEY` olarak kaydet

### Seçenek C — Groq (Llama 70B, Tamamen Ücretsiz)
- **Limit:** 14,400 istek/gün — çok cömert
- **Maliyet:** $0
- **Hız:** En hızlı ücretsiz seçenek (özel donanım)
- **Nasıl alınır:**
  1. https://console.groq.com adresine git
  2. Kayıt ol → API Keys → Create
  3. `GROQ_API_KEY` olarak kaydet

### Seçenek D — Google AI Studio (Gemini Flash-Lite)
- **Limit:** 1,000 istek/gün, 15 RPM
- **Maliyet:** $0
- **Nasıl alınır:**
  1. https://aistudio.google.com adresine git
  2. Google hesabıyla giriş yap
  3. "Get API Key" → Create
  4. `GEMINI_API_KEY` olarak kaydet

### Seçenek E — DeepSeek (Neredeyse Ücretsiz)
- **Fiyat:** $0.03/milyon token
- **9,900 örnek için:** ~$2-3
- **Kalite:** GPT-4 seviyesi
- **Nasıl alınır:**
  1. https://platform.deepseek.com adresine git
  2. Kayıt ol → API Keys → Create
  3. `DEEPSEEK_API_KEY` olarak kaydet

### Seçenek F — Ollama (Tamamen Local, $0)
- **Maliyet:** $0
- **Nasıl alınır:**
  1. https://ollama.com indir
  2. `ollama pull llama3.2:3b`
  3. `ollama serve`

---

## Maliyet Karşılaştırması

| Platform | Model | Maliyet | Kalite | Hız |
|----------|-------|---------|--------|-----|
| AIML API | Claude+GPT+Gemini | $0* | ⭐⭐⭐⭐⭐ | Orta |
| OpenRouter | 500+ model | $0* | ⭐⭐⭐⭐ | Hızlı |
| Groq | Llama 70B | $0 | ⭐⭐⭐⭐ | Çok Hızlı |
| Gemini | Flash-Lite | $0 | ⭐⭐⭐ | Hızlı |
| DeepSeek | R1 Distill | ~$2-3 | ⭐⭐⭐⭐ | Hızlı |
| Ollama | Llama 3.2 3B | $0 | ⭐⭐ | Yavaş |
| Claude Sonnet | Orijinal | ~$45-65 | ⭐⭐⭐⭐⭐ | Orta |

*Ücretsiz kredi/tier dahilinde

---

## TAVSİYE: $0 Hibrit Strateji

```
AIML API      (weight=0.5) → Claude/GPT kalitesi, ücretsiz kredi
Groq          (weight=0.3) → Llama 70B, hızlı, sınırsız
Gemini        (weight=0.2) → Flash-Lite, yedek
Toplam maliyet: $0
```

---

## 2. HAZIRLIK ADIMLARI

### Adım 1 — API Keyleri Topla

Öncelik sırası:
1. **AIML API** → https://aimlapi.com (en önemli)
2. **Groq** → https://console.groq.com
3. **Gemini** → https://aistudio.google.com
4. **OpenRouter** → https://openrouter.ai (yedek)

```bash
# .env dosyası oluştur (repo kökünde)
AIMLAPI_KEY=your_key_here
GROQ_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
OPENROUTER_KEY=your_key_here
# Opsiyonel:
DEEPSEEK_API_KEY=your_key_here
```

### Adım 2 — Colab'ı Hazırla
1. https://colab.research.google.com adresine git
2. Yeni notebook aç
3. Runtime → Change runtime type → **T4 GPU** seç (ücretsiz)

### Adım 3 — Repoyu Clone Et
```python
!git clone https://github.com/mk350174-cmd/Persona.git
%cd Persona
!pip install -r needle/training/requirements.txt
!pip install -r needle/finetune/requirements.txt
!pip install groq google-generativeai openai  # AIML API OpenAI uyumlu
```

### Adım 4 — Keyleri Ayarla
```python
import os
os.environ["AIMLAPI_KEY"] = "your_key"
os.environ["GROQ_API_KEY"] = "your_key"
os.environ["GEMINI_API_KEY"] = "your_key"
```

---

## 3. TEACHER PATCH — Claude Code'a At

Önce şu patch'i Claude Code'a gönder:

```
needle/training/teachers/ klasörüne 3 yeni teacher ekle:

## aiml_teacher.py (weight=0.5)
class AIMLTeacher(BaseTeacher):
    weight = 0.5
    # AIML API OpenAI uyumlu endpoint kullanır
    # base_url = "https://api.aimlapi.com/v1"
    # model = "claude-3-5-sonnet-20241022" (ücretsiz kredide)
    # OpenAI SDK ile:
    # from openai import OpenAI
    # client = OpenAI(
    #   api_key=os.environ["AIMLAPI_KEY"],
    #   base_url="https://api.aimlapi.com/v1"
    # )
    # Claude Teacher ile aynı 3 prompt (CEID/DRIFT/VOICE)
    # Rate limit: 60 RPM
    # Cache mekanizması aynı
    # Fallback: persona_math.ceid

## groq_teacher.py (weight=0.3)
class GroqTeacher(BaseTeacher):
    weight = 0.3
    # model = "llama-3.1-70b-versatile"
    # from groq import Groq
    # client = Groq(api_key=os.environ["GROQ_API_KEY"])
    # Rate limit: 10 RPM güvenli (14,400/gün)
    # Cache mekanizması aynı
    # Fallback: persona_math.ceid

## openrouter_teacher.py (weight=0.2, yedek)
class OpenRouterTeacher(BaseTeacher):
    weight = 0.2
    # OpenAI uyumlu endpoint:
    # base_url = "https://openrouter.ai/api/v1"
    # model = "meta-llama/llama-3.1-70b-instruct:free"
    # Ücretsiz modeller için rate limit düşük olabilir
    # Cache + fallback mekanizması aynı

## pipeline.py güncelle
AIMLTeacher, GroqTeacher, OpenRouterTeacher ekle.
ClaudeTeacher artık opsiyonel (pahalı, atlanabilir).

## Ağırlık normalizasyonu
Hangi teacher'lar aktifse ağırlıkları otomatik normalize et:
total_weight = sum(t.weight for t in active_teachers)
normalized = t.weight / total_weight

## Testler güncelle
Yeni 3 teacher için mock testler ekle.
pytest hedef: 400+ passed
```

---

## 4. EĞİTİM VERİSİ ÜRET

```python
# Colab'da çalıştır
# AIML API + Groq + Gemini (Claude yok, $0)

!python -m needle.training.pipeline \
  --aiml-key $AIMLAPI_KEY \
  --groq-key $GROQ_API_KEY \
  --gemini-key $GEMINI_API_KEY \
  --n-conversations 20 \
  --resume

# Tahmini süre: 2-4 saat (Groq çok hızlı)
# Checkpoint var — yarıda kesilirse --resume ile devam
# Üretilecek: ~9,900 örnek (495 persona × 20)
```

### Günlük Limit Yönetimi

| Platform | Limit | Kaç günde biter? |
|----------|-------|------------------|
| Groq | 14,400/gün | 1 gün |
| AIML API | Kredi bazlı | 1-2 gün |
| Gemini Flash-Lite | 1,000/gün | 10 gün |

**Groq'u ana kaynak yap** → 1 günde tamamlanır.

---

## 5. MODELİ EĞİT

```python
# T4 GPU ile (Colab ücretsiz)
!python -m needle.finetune.trainer \
  --train needle/training/data/train.jsonl \
  --val needle/training/data/val.jsonl \
  --lora \
  --epochs 3 \
  --device cuda \
  --batch-size 16 \
  --checkpoint-dir needle/finetune/checkpoints/

# Tahmini süre T4'te: 4-6 saat
```

### Beklenen Eğitim Çıktısı
```
Epoch 1/3 | train_loss: 0.423 | val_loss: 0.389
  CEID MAE: 0.067 | Drift F1: 0.81 | Perplexity: 31.2

Epoch 2/3 | train_loss: 0.312 | val_loss: 0.298
  CEID MAE: 0.048 | Drift F1: 0.87 | Perplexity: 26.8

Epoch 3/3 | train_loss: 0.251 | val_loss: 0.243
  CEID MAE: 0.038 | Drift F1: 0.91 | Perplexity: 23.1

✓ Hedefler tuttu:
  MAE < 0.05 ✓ (0.038)
  F1 > 0.88  ✓ (0.91)
  PPL < 25   ✓ (23.1)
```

> NOT (dürüstlük): Yukarıdaki sayılar **hedef/örnek** çıktıdır, ölçülmüş değil.
> Gerçek metrikler eğitim Colab'da çalıştırılınca üretilir; ancak ondan sonra
> tier "Ölçülmüş" olur (bkz. validation/README.md).

---

## 6. QUANTIZATION + BUNDLE

```python
# INT4 quantization
!python -m needle.finetune.quantize.int4 \
  --model needle/finetune/checkpoints/best_model/ \
  --output needle/finetune/quantize/output/

# GGUF export
!python -m needle.finetune.quantize.gguf_writer \
  --quantized needle/finetune/quantize/output/ \
  --output needle/finetune/quantize/output/model.gguf

# Boyut kontrolü (~13MB olmalı)
!ls -lh needle/finetune/quantize/output/*.gguf

# İlk persona bundle (test)
!python -m needle.finetune.export.persona_bundler \
  --persona-id socrates \
  --gguf needle/finetune/quantize/output/model.gguf \
  --output needle/bundles/

# manifest.json kontrol
!cat needle/bundles/socrates/manifest.json
# "untrained": false ✓
# "total_size_mb": 15-20 ✓

# Tüm 495 persona (paralel)
!python -m needle.pipeline.bulk_bundler \
  --workers 4 --resume
```

---

## 7. AKADEMİK VALİDASYON

```python
# M1-M60 tier güncelle: Simülasyon → Ölçülmüş
# (yalnızca eğitilmiş checkpoint yüklenince gerçekleşir)
!python -m validation.validator --all --workers 2

# M61 sonuçlarını güncelle
!python papers/M61_experiments/exp_m61.py \
  --checkpoint needle/finetune/checkpoints/best_model/

# Rapor üret
!python -m validation.report_generator \
  --output validation/REPORT.md

!cat validation/REPORT.md
# Tier dağılımı (eğitim sonrası hedef):
# Önce: Simülasyon:54, Tahmini:46, Ölçülmüş:0
# Sonra: Ölçülmüş:51+, Hesaplanan:9, Tahmini:0
```

> NOT: PersonaNeedle eğitilmeden bu komut persona_math.ceid fallback'i kullanır
> ve tier "Ölçülmüş" OLMAZ (Simülasyon kalır). Measured tier'ı yalnızca gerçek
> (eğitilmiş, untrained=False) ölçüm açar.

---

## 8. M2 MDPI GÖNDERİMİ

### Adım 1 — PDF Derle
```python
# Colab'da LaTeX kur
!apt-get install texlive-full -y 2>/dev/null

# M2 derle
!cd submissions/M2 && pdflatex M2_*.tex
!cd submissions/M2 && pdflatex M2_*.tex  # 2 kez

# Kontrol
!ls -lh submissions/M2/*.pdf
```

### Adım 2 — Yazar Bilgilerini Doldur
submissions/M2/ klasöründe .tex dosyasını aç:
```latex
% Şunları doldur:
\author{[İsmin veya "Independent Researcher"]}
\affiliation{[Bağımsız Araştırmacı]}
\email{[email@adresin]}
```

### Adım 3 — Cover Letter
```
Dear Editors of Entropy (MDPI),

We submit "The Mandatory Core: Topological Necessity of
a Stable Identity Kernel in LLM Persona Systems" for
consideration in Entropy.

This paper introduces the Mandatory Core architecture —
a topologically stable identity kernel validated through
the CEID protocol across 495 personas and 9,900 simulated
conversations.

The manuscript has not been published elsewhere.

Sincerely,
[İsim]
Independent Researcher
```

### Adım 4 — MDPI'ya Yükle
1. https://www.mdpi.com/journal/entropy
2. "Submit a Manuscript"
3. Kayıt ol / giriş yap
4. PDF + LaTeX kaynak dosyalarını yükle
5. Cover letter ekle
6. Gönder → Onay emailini bekle

---

## 9. REPO GÜNCELLE

```python
!git config user.email "email@adresin"
!git config user.name "İsmin"

!git add needle/finetune/checkpoints/best_model/
!git add needle/bundles/catalog.json
!git add validation/REPORT.md
!git add results/M61/

!git commit -m "feat: PersonaNeedle trained — \
  untrained:False, 495 personas bundled, \
  M1-M60 tiers updated to Measured"

!git push origin claude/inspiring-hopper-1qnKP
```

---

## TOPLAM MALİYET

| Kalem | Platform | Maliyet |
|-------|----------|---------|
| Eğitim verisi üretimi | AIML API + Groq + Gemini | $0 |
| Fine-tune GPU | Colab T4 | $0 |
| Quantization | Colab | $0 |
| MDPI submission | Entropy | $0 |
| **TOPLAM** | | **$0** |

Opsiyonel kalite artışı için DeepSeek: ~$2-3

---

## TAHMİNİ ZAMAN ÇİZELGESİ

| Gün | Aksiyon | Süre |
|-----|---------|------|
| 1 | API keyleri al, Colab hazırla | 1 saat |
| 1 | Teacher patch → Claude Code | 30 dakika |
| 1-2 | Veri üretimi (Groq hızlı) | 2-4 saat |
| 2 | Fine-tune (Colab T4) | 4-6 saat |
| 2 | Quantization + bundle | 1 saat |
| 3 | Validasyon + M61 güncelle | 2 saat |
| 3 | M2 PDF derle + MDPI gönder | 1 saat |
| **3 gün** | **Tamamlandı** | **~$0** |

---

## FAYDALI LİNKLER

| Platform | URL | Ne İçin |
|----------|-----|---------|
| AIML API | https://aimlapi.com | Ana öğretmen |
| Groq | https://console.groq.com | Hızlı Llama |
| Gemini | https://aistudio.google.com | Yedek |
| OpenRouter | https://openrouter.ai | 500+ model |
| Colab | https://colab.research.google.com | GPU eğitim |
| MDPI Entropy | https://mdpi.com/journal/entropy | M2 gönderim |
| public-apis | https://github.com/public-apis/public-apis | API listesi |
| Türkçe APIs | https://github.com/MertMURAT/public-api-deposu | TR API listesi |
| Turkish APIs | https://github.com/3rt4nm4n/turkish-apis | TR API listesi |
