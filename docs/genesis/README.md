# docs/genesis/ — Tasarım/Genesis Materyalleri

Bu klasördeki üç `.docx` dosyası, mevcut kod ve makalelerin **öncesine
ait ham tasarım materyalleri** — akran değerlendirmesinden geçmiş
makaleler değil, sistemin kavramsal kökeni. Değiştirilmeden, olduğu gibi
saklanıyor (`docs/denetim/` klasörüyle aynı ilke: ham kanıt bozulmaz).

## Dosyalar

### `SAYFA_1-20_CEID_v2_Genesis.docx` (eski ad: "SAYFA 1- ...")
20 sayfalık bir tasarım günlüğü — CEID v2.0 / 8-patch mimarisinin
(4D Vizör, Stokastik Rezonans, Diyalektik Amortisör, Heisenberg Tamponu,
Otopoietik İsyan, Jungiyen Arketip, Sisyphus Geri Kazanım) kavramsal
kökeni. **T1-151'de doğrulandı:** `persona_math/ceid.py`'deki 8 patch
fonksiyonu isim isim bu belgenin SAYFA 2-8 bölümleriyle eşleşiyor — kod
ile bu belge önceki turlarda hiç bağlanmamıştı, şimdi hem `ceid.py`'nin
docstring'inde hem `docs/ceid_v2_8patch_status.md`'de çapraz referans
var. Bu belge bir makale **değil** — 8-patch mimarisi hâlâ hiçbir M1-M77
makalesinde akran değerlendirmesinden geçmedi, tier'ı Simülasyon/Tahmini
kalıyor.

### `KOMBİNASYON_1-250_Hibrit_Persona_Katalogu.docx` (eski ad: "KOMBİNASYON 1- ...")
250 hibrit persona kombinasyonunun tam kataloğu (K-layer aktif/baskılanan
katman listeleriyle). `scripts/docx_parser.py` (persona-platform) bu
belgeyi ayrıştırıp `data/hybrid_personas_raw.jsonl`'i üretiyor —
**T1-158'de bir ayrıştırma hatası bulundu ve düzeltildi** (görünmez
sıfır-genişlikli boşluk karakteri yüzünden 250 kayıttan sadece 48'i
doğru ayrıştırılıyordu; düzeltme sonrası 250/250 doğru).

**T1-152 doğrulama sonucu:** Bu katalogdaki 250 kombinasyon, M4'ün
"Court of 250" deneyindeki 250 persona ile **AYNI VERİ DEĞİL**. M4'ün
seti gerçek filozof isimleriyle (Wittgenstein, Kant, Confucius, vb.)
kurulu; bu katalog arketipsel rol isimleriyle (Saf Rasyonalist, Radikal
Şüpheci, vb.) kurulu. 250 sayısının eşleşmesi **muhtemelen tesadüfi** —
M4'e bu belgeden doğrudan bir atıf eklenmedi çünkü kanıt yetersiz;
gelecekte gerçek bir bağlantı bulunursa `papers/M4_Adalet_Sarayi_v3.tex`e
not düşülmeli.

### `Katman_1-Ontolojik_Kok.docx` (eski ad: "Katman 1- ...")
K-layer taksonomisinin (K1-K8 arası detaylı) erken tasarım tanımları.

**⚠️ T1-155 — ÇÖZÜLMEMİŞ ÇAKIŞMA:** Bu belge **K5 = "Baskı ve Savunma
Mekanizması"** ve **K6 = "İdiosenkratik Pürüzler (Sentetik Hata Payı)"**
tanımlıyor. Ama güncel, yayınlanmış makaleler farklı tanımlar kullanıyor:
- **M62** (`M62_K5_Temporal_Identity_v01.tex`): K5 = "Temporal Identity
  Layer" (kişisel süreklilik/kronobiyoloji) — bu genesis belgesiyle
  **hiç ilgisi yok**.
- **M45** (`submissions/M45/M45_Ruhsal_K6_v01.tex`): K6 = "Archetypal
  Foundation" (Jung arketipleri) — bu genesis belgesindeki "sentetik
  hata payı" tanımıyla da **çelişiyor**.

Bu, K-layer numaralandırmasının zamanla yeniden kullanıldığının ikinci
kanıtı (bkz. `AUDIT_FINDINGS.md` — `docs/cepheler`'deki M64
tartışmasıyla aynı örüntü). **Düzeltme (T1-164 sırasında):**
`persona_math/consciousness.py`'nin "M22-M25" docstring'i başlangıçta bu
örüntünün üçüncü örneği sanılmıştı, ama araştırınca **öyle olmadığı
ortaya çıktı** — `persona_math/__init__.py` kendi 55-araç iç numaralama
şemasını (M01-M55, her alt modül için bir aralık) belgeliyor ve
`M7_Matematiksel_Cerceve_v4.tex`'in kendisi "Group XI: Quantum
Mathematical Analogues (M40--M43)" gibi tablolarla bu iç şemayı zaten
tanımlıyor — yani `persona_math/*.py`'deki "Mxx" referansları çoğunlukla
M7'nin kendi iç araç indeksine doğru atıfta bulunuyor, makale serisine
değil. Bkz. `validation/check_docstring_paper_refs.py`'nin docstring'i
bu ayrımı detaylandırıyor. **Çözülmedi** (K5/K6 çakışması, yukarıdaki):
hangi tanımın kanonik olduğuna (muhtemelen en güncel makale: M62/M45)
resmi bir karar `AUDIT_FINDINGS.md`'ye düşülmeli, bu README sadece
çakışmayı kayıt altına alıyor.
