# ADR 0001 — Web/App Katmanının Yeniden İnşası: Mimari Kararlar

**Durum:** Kabul edildi (2026-07-30)
**Kaynak:** `GELISTIRME_GOREV_LISTESI.txt` Track 2, T2-001-006.
**Bağlam:** Bu reponun eski web/app katmanı (`api/`, `frontend/`, `mobile/`,
`alembic/`, vb.) 29 Temmuz 2026'da kaldırıldı — denetim, kapsamlı ama
büyük ölçüde işletilmemiş checklist'ler, boş sign-off şablonları ve
"tamamlandı" denip hiç çalıştırılmamış test iddiaları buldu (bkz.
`AUDIT_FINDINGS.md` AF-P-005/P-007). Bu ADR, o katmanın **sıfırdan, aynı
teknoloji yığınıyla ama bu kez checklist'ler gerçekten işletilerek**
yeniden inşa edilmesinin kararlarını kayıt altına alıyor.

## T2-001 — Backend Stack

**Karar: FastAPI + PostgreSQL korunuyor** (kullanıcı onayı, 2026-07-30).

Gerekçe: `persona_math`/`needle`/`persona_mcp` zaten Python; FastAPI'nin
async desteği WebSocket sohbet (T2-016) için uygun; eski kod tabanının
büyük kısmı (auth, ödeme, middleware deseni) mimari olarak sağlamdı —
sorun mimaride değil, süreç disiplinindeydi (checklist'lerin
işletilmemesi). Değiştirmek yeni bir risk yüzeyi açardı, mevcut sorunu
çözmezdi.

## T2-002 — Frontend Stack

**Karar: React korunuyor** (kullanıcı onayı, 2026-07-30).

Gerekçe: aynı — sorun React'te değildi. `vite`/`create-react-app` yerine
hangi araç setinin kullanılacağı Faz 5'te (frontend inşası) belirlenir.

## T2-003 — persona_mcp Entegrasyonu

**Karar: REST wrapper** — `persona_mcp`'nin araçları (`get_persona_profile`,
`measure_persona_ceid`, `detect_drift`, vb.) doğrudan FastAPI router'ları
tarafından çağrılır (`persona_mcp.tools.persona_tools` içe aktarılıp
handler fonksiyonları sarmalanır), MCP protokolünün kendisi web/app
katmanına taşınmaz. Eski `api/needle_service.py`'nin torch-safe lazy-import
+ `persona_math.ceid` fallback deseni (CLAUDE.md "graceful degradation"
ilkesi) referans alınır — **kopyalanmaz**, yeniden yazılır.

Gerekçe: `persona_mcp` zaten Claude Code'un kendi MCP entegrasyonu için
var (`.mcp.json`); web/app katmanının ayrıca bir MCP istemcisi çalıştırması
gereksiz karmaşıklık ekler. Doğrudan Python içe aktarma daha basit, daha
hızlı, ve `untrained` bayrağının (T2-018) uçtan uca taşınmasını kolaylaştırır.

## T2-004 — Eski Kod Kullanım Politikası

**Karar: Denetimden geçirerek yeniden yazma, kopyalama değil.**

Eski `api/` kodu (bu oturumun git geçmişinde hâlâ mevcut,
`git show <eski-commit>:api/...` ile erişilebilir) **desen referansı**
olarak kullanılabilir (örn. `payments.py`'nin Stripe webhook doğrulama
mantığı, `security_headers.py`'nin OWASP header seti) ama satır satır
kopyalanmaz. Her yeniden yazılan modül:
1. Gerçekten çalıştırılıp test edilir (eski kodun "47 test" iddiası
   gerçek değildi — bkz. AUDIT_FINDINGS AF-P-007 benzeri bulgular)
2. Checklist/sign-off dosyaları gerçek durumu yansıtır (`0/N` ise
   `0/N` yazılır, "tamamlandı" denmez)

## T2-005 — `personaplatform.zip`

**Karar: Silinecek.** İçeriği zaten önceki entegrasyon turlarında
(`needle`/`persona_math`/`persona_mcp` migrasyonu) çıkarılıp repoya
işlendi; kalan `api/` kodu bu ADR'nin kendisi referans olarak kullanıyor
(git geçmişinden). Artık aktif bir amaca hizmet etmiyor, sadece kafa
karıştırıyor ("bu zip mi güncel yoksa repo mu?").

## T2-006 — Bu Belge

Bu ADR, T2-001-006'nın resmi kaydıdır. Sonraki fazlar (Backend/Frontend/
CI-CD/Hukuki/Lansman) bu kararlara göre ilerler; herhangi bir sapma yeni
bir ADR (`0002-...`) gerektirir.
