# Doküman Konsolidasyon Planı (Ertelendi)

**Kaynak:** `AUDIT_FINDINGS.md` AF-P-011 (2026-07-29).

## Neden ertelendi

Denetim 4 doküman kümesinde şişkinlik buldu (aynı konuda 3-11 dosya).
Bu oturumda `docs/cepheler/` kümesini (Persona repo) başarıyla
konsolide ettik çünkü o dosyalar kısaydı ve büyük ölçüde yinelenen/
fabrike içerikti. Bu platformdaki kümeler farklı: her biri **400-1300
satırlık, gerçek operasyonel prosedürler** içeriyor (deployment
adımları, runbook komutları, checklist'ler). Bunları aceleyle
birleştirmek, dikkatli okuma yapılmadan gerçek bir prosedürün
kaybolmasına yol açabilir — bu, konsolidasyonun çözmeye çalıştığı
sorundan (tutarsızlık riski) daha kötü bir sonuç olur.

## Kümeler ve boyutları

| Küme | Dosyalar | Toplam satır |
|---|---|---|
| HYBRID_PERSONAS | DEPLOYMENT (417), INTEGRATION (751), PRODUCTION_READINESS (397) | 1565 |
| STAGING | DEPLOYMENT (760), DEPLOYMENT_GUIDE (541), DEPLOYMENT_RUNBOOK (1323) | 2624 |
| LOAD_TESTING | 5 dosya | (ölçülmedi — ayrı oturumda ele alınmalı) |
| TURKISH | 11 dosya | (ölçülmedi — ayrı oturumda ele alınmalı) |

## Önerilen yaklaşım (gelecek oturum için)

Her küme için:
1. Tüm dosyaları tam okuyun — hangi prosedürler benzersiz, hangileri
   gerçekten yinelenen?
2. En güncel/en kapsamlı dosyayı kanonik olarak seçin.
3. Diğer dosyalardaki **benzersiz** içeriği (varsa) kanonik dosyaya
   taşıyın — sadece silmeyin.
4. Yinelenen dosyaları `docs/archive/`'a taşıyın, kanonik dosyaya
   işaret eden bir not bırakın.
5. Kod/CI'da bu dosyalara referans var mı kontrol edin (script'ler,
   README'ler) — varsa güncelleyin.

Bu, `cepheler/` konsolidasyonunda kullanılan yöntemin aynısı, sadece
her kümenin gerçek prosedür içeriğini kaybetmemek için daha dikkatli
bir okuma turu gerektiriyor.
