# Privacy Policy / Gizlilik Politikası

> **⚠️ TASLAK — HUKUKÇU ONAYI GEREKLİ, YÜRÜRLÜKTE DEĞİL ⚠️**
>
> Bu belge bir taslaktır. Bir avukat (tercihen GDPR/KVKK deneyimli)
> tarafından incelenip onaylanana kadar yürürlükte değildir ve
> kullanıcılara sunulmamalıdır. `PRODUCTION_CHECKLIST.md`'de "GDPR
> compliance" ve "Privacy policy" işaretlenmemiş madde olarak listeli —
> bu taslak o boşluğu doldurmaya başlıyor, GDPR/KVKK uyumluluğunu tek
> başına sağlamıyor. Denetim kaynağı: `AUDIT_FINDINGS.md` AF-P-002.

**Son güncelleme: [TARİH GİRİLECEK]**

## 1. Topladığımız Veriler

Kod tabanına (`api/models.py`, `api/payments.py`) dayanarak, gerçekte
toplanan veriler:

| Veri türü | Kaynak | Amaç |
|---|---|---|
| E-posta adresi | Kayıt formu | Hesap oluşturma, e-posta doğrulama |
| Şifre (hash'lenmiş) | Kayıt formu | Kimlik doğrulama |
| Ödeme bilgileri | Stripe (bizde saklanmaz) | Abonelik/ödeme işleme |
| Persona etkileşim geçmişi | Uygulama kullanımı | Hizmetin çalışması, CEID/K-layer analizi |
| [DOLDURULACAK] | | Gerçek veri envanteri tamamlanmalı — bu tablo
  koddan çıkarılan bir başlangıç noktasıdır, eksiksiz olduğu garanti
  edilmez. |

## 2. Verileri Nasıl Kullanıyoruz

- Hesabınızı yönetmek ve Hizmet'i sağlamak için.
- Ödemeleri işlemek için (Stripe aracılığıyla; kart bilgileri bizim
  sunucularımıza ulaşmaz).
- [AVUKAT ONAYI GEREKLİ: analitik/pazarlama amaçlı kullanım varsa
  açıkça belirtilmeli ve ayrı onay mekanizması gerekebilir.]

## 3. Verileri Kimlerle Paylaşıyoruz

- **Stripe** (ödeme işleme) — Stripe'ın kendi gizlilik politikasına
  tabidir.
- [AVUKAT ONAYI GEREKLİ: başka üçüncü taraf servis sağlayıcı var mı
  (analytics, e-posta gönderimi, hosting) — her biri burada
  listelenmeli.]

## 4. Veri Saklama

[AVUKAT ONAYI GEREKLİ: hesap silindiğinde veriler ne kadar süre
saklanır, persona etkileşim geçmişi ne zaman silinir.]

## 5. Kullanıcı Hakları (GDPR/KVKK)

Yargı yetkisine bağlı olarak şu haklara sahip olabilirsiniz:
- Verilerinize erişim talep etme
- Verilerinizin düzeltilmesini talep etme
- Verilerinizin silinmesini talep etme ("unutulma hakkı")
- Veri işlemeye itiraz etme
- Veri taşınabilirliği

[AVUKAT ONAYI GEREKLİ: bu hakların nasıl kullanılacağına dair somut
süreç (hangi e-postaya yazılacak, yanıt süresi) eklenmeli. Şu anda
sadece hakların listesi var, işletilebilir bir süreç yok.]

## 6. Çocukların Gizliliği

[AVUKAT ONAYI GEREKLİ: 13/16 yaş altı kullanıcı politikası — COPPA/
GDPR-K gerekliliklerine göre netleştirilmeli.]

## 7. Veri Güvenliği

Şifreler hash'lenerek saklanır. Ödeme verileri hiç sunucularımıza
ulaşmaz (Stripe Checkout kullanılıyor). [AVUKAT ONAYI GEREKLİ: şifreleme
standartları, ihlal bildirim süreci (GDPR 72 saat kuralı gibi) açıkça
yazılmalı.]

## 8. Uluslararası Veri Aktarımı

[AVUKAT ONAYI GEREKLİ: sunucular hangi ülkede, AB kullanıcıları için
Standard Contractual Clauses gerekip gerekmediği.]

## 9. İletişim

[AVUKAT ONAYI GEREKLİ: Veri Sorumlusu (Data Controller) unvanı, KVKK
için VERBİS kaydı gerekip gerekmediği, iletişim e-postası.]

---

*Bu taslak, `mk350174-cmd/persona-platform` reposunun 2026-07-29 tarihli
denetimine (AF-P-002) cevaben hazırlandı — Bölüm 1'deki veri tablosu
gerçek `api/models.py`/`api/payments.py` koduna dayanıyor, geri kalanı
şablon metindir. Yürürlüğe girmeden önce mutlaka bir avukat tarafından
gözden geçirilmelidir.*
