# CLAUDE.md — Persona Repo | Token Optimize & Çoklu Model

> **Terminoloji:** Kanonik terimler için Persona repo'sundaki `GLOSSARY.md` tek doğruluk kaynağıdır.

## Bu Repo Hakkında
Persona mühendisliği ekosistemi: 495 K-layer persona (100-dim), PersonaNeedle 74.2M SAN modeli,
77 akademik makale (M1-M77, M1-M24 çekirdek), persona_mcp (8 tool), Android runtime, akademik validasyon.

Repo yapısı:
- persona_math/    → K-layer vektörleri
- needle/          → PersonaNeedle (architecture/training/finetune/pipeline)
- persona_mcp/     → MCP server + Logseq entegrasyonu
- papers/          → M1-M61 LaTeX makaleleri
- validation/      → Akademik tier güncelleme
- android/         → Kotlin runtime
- submissions/     → Gönderime hazır paketler

---

## MODEL SEÇİM KURALLARI

### Claude Code (Sen) → Şu işleri yap:
- Mimari kararlar ve patch planlaması
- K-layer matematik ve CEID algoritması
- Kritik business logic (trainer, distillation, quantizer)
- Hata ayıklama ve test yazımı
- PR açma ve merge

### Gemini CLI → Şu işlere yönlendir:
- 500+ satırlık dosya okuma (needle/architecture/san.py, papers/*.tex)
- Tüm repo taraması gereken analizler
- Web'den güncel API/kütüphane bilgisi
- Uzun JSONL veri dosyaları okuma
Komut: `/gemini:investigate <görev>`

### Codex → Şu işlere yönlendir:
- Yeni teacher dosyaları (aiml_teacher.py, groq_teacher.py vb.)
- Boilerplate test dosyaları
- README ve dokümantasyon güncellemeleri
- requirements.txt güncellemeleri
Komut: `/codex <görev>`

### Ollama (lokal) → Şu işlere yönlendir:
- Tekrarlayan, düşük riskli görevler
- Sıfır maliyetli deneme/prototip
- Groq dolduğunda yedek

---

## TOKEN TASARRUF KURALLARI

1. **Büyük dosyaları okuma** — Gemini'ye ver, özet iste
2. **%80 dolduğunda** — oturumu kapat, yeni başlat
3. **Patch'ler küçük olsun** — tek oturumda max 3 dosya
4. **MCP server sayısı** — max 4 aktif tut (GitHub + Memory + Context7 + 1 ekstra)
5. **Kullanmadığın MCP'leri kapat** — her biri context yiyor

## AKTİF MCP SUNUCULAR (Sadece Bunlar)
- github → PR, issue, repo yönetimi
- memory → Projeler arası hafıza
- context7 → Güncel dokümantasyon
- filesystem → needle/ ve papers/ dışı erişim

---

## MEVCUT DURUM (Haziran 2026)

### Tamamlanan
- [x] PATCH-01..10 tüm ekosistem kuruldu
- [x] 441 test geçiyor (12 skip — torch gerektiriyor)
- [x] 495 persona bundle (untrained=True)
- [x] M1-M61 makaleler finalize
- [x] PR #10 + #11 merge edildi

### Bekleyen (Öncelik Sırası)
1. Teacher patch → aiml_teacher.py, groq_teacher.py, openrouter_teacher.py
2. Eğitim verisi üretimi (AIML + Groq, $0)
3. Colab T4 fine-tune (4-6 saat)
4. Quantization + 495 persona bundle (untrained→False)
5. M1-M60 tier güncelleme (Simülasyon → Ölçülmüş)
6. M2 PDF derle + MDPI gönder

---

## YAYIN BÜTÜNLÜĞÜ KURALLARI (İSTİSNASIZ)

> Kaynak: 77 makalelik denetim. Kanonik kayıt: Persona repo'sundaki
> `AUDIT_FINDINGS.md` + `docs/denetim/`.
> Bu üç kural M72 (insan verisi fabrikasyonu riski) ve M7 (dayanaksız Bell
> Inequality iddiası) gibi bulguların tekrarını önlemek için konuldu.

1. **Tier etiketi zorunlu.** Her yeni veya düzenlenen makalede
   `Ölçülmüş / Hesaplanan / Simülasyon / Tahmini` etiketlerinden biri
   bulunmak zorundadır — istisnasız. Etiketsiz sayısal iddia yayınlanamaz.

2. **Klinik/insan-özneli iddialar M28 şablonuna uyar.** İnsan öznesi içeren
   her bölüm M28'in üçlü yapısını taşımak zorundadır:
   *appropriate for* / *not appropriate for* / *currently unvalidated*.
   Gerçek tanı kategorisi, tedavi yöntemi ya da eşik değeri öneren hiçbir
   tablo bu şablon olmadan yayınlanamaz.

3. **Placeholder içeriği "tam manuscript" gibi sunulamaz.** Toplu/otomatik
   üretilmiş yer tutucu metinlerin kaynağı açıkça belirtilmek zorundadır.
   Yer tutucudan gelen N sayıları, r değerleri ve yüzdeler etiketsiz olarak
   "tam" versiyona taşınamaz.

**Platform tarafı ek kural:** `agents/*.md` altındaki tarihi kişi personaları
AI-simülasyon disclaimer'ı olmadan yayınlanamaz (bkz. `AF-P-001`).

---

## ÇALIŞMA PRENSİPLERİ

- **Dürüst tier**: "Measured/Ölçülmüş" sadece gerçek ölçüm sonrası
- **Torch-free**: Her modül torch olmadan import edilebilmeli
- **Checkpoint**: Uzun işlemler kesintisiz devam edebilmeli
- **Graceful degradation**: API yoksa persona_math.ceid fallback
- **495 persona**: 534 değil — gerçek library boyutu bu

---

## PIPELINE HATIRLATMA

```
Gemini → uzun dosyayı oku + özetle
Claude → mimari karar ver
Codex  → boilerplate yaz
Claude → kritik logic yaz + test et
GitHub MCP → PR aç + merge
```
