# 🚀 Persona Platform — Production Launch Setup Guide

**Sürüm:** 1.0.0  
**Tarih:** 2026-06-12  
**Durum:** ✅ Tüm Tier 1 entegrasyonlar tamamlandı

---

## 📋 Hızlı Başlangıç (Quick Start)

### 1. Harici Hizmetleri Ayarla (30 dakika)

#### Sentry - Hata İzleme
```bash
# https://sentry.io/signup/ adresine git
1. Organization oluştur: "Persona Platform"
2. Project oluştur: Python → FastAPI
3. DSN kopyala: https://exampleKey@o0.ingest.sentry.io/0
```

#### PostHog - Analitikler
```bash
# https://posthog.com/signup adresine git
1. Organization oluştur
2. Project oluştur
3. API Key kopyala: phc_...
4. Host seç: https://eu.posthog.com (EU) veya https://us.posthog.com (US)
```

#### Resend - E-posta Servisi
```bash
# https://resend.com/signup adresine git
1. API Key al: re_...
2. Sender domain yapılandır: noreply@yourdomain.com
3. Test e-postas gönder
```

#### Supabase - Dosya Depolama (İsteğe bağlı)
```bash
# https://supabase.co dashboard
1. Üç bucket oluştur:
   - user-avatars (public)
   - persona-assets (public)
   - compiled-configs (private)
2. Service Role Key al
```

### 2. Vercel'de Secrets Ekle (15 dakika)

```bash
# https://vercel.com/persona-platform → Settings → Environment Variables

# Ödeme
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Hata İzleme
SENTRY_DSN=https://exampleKey@o0.ingest.sentry.io/0
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_PROFILES_SAMPLE_RATE=0.1

# Analitikler
POSTHOG_API_KEY=phc_...
POSTHOG_HOST=https://eu.posthog.com

# E-posta
RESEND_API_KEY=re_...
FROM_EMAIL=noreply@yourdomain.com

# Dosya Depolama (opsiyonel)
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOi...

# Veritabanı
DATABASE_URL=postgresql://user:pass@host:5432/db

# Güvenlik
JWT_SECRET_KEY=<openssl rand -hex 32 çıktısı>

# Dağıtım
ENVIRONMENT=production
APP_VERSION=1.0.0
BASE_URL=https://api.yourdomain.com
```

### 3. Ortamı Test Et (30 dakika)

```bash
# Staging deploy
git push origin main

# Health check
curl https://staging-api.yourdomain.com/health

# Hata testini tetikle
curl -X POST https://staging-api.yourdomain.com/observability/logs/collect \
  -H "X-API-Key: test_key" \
  -H "Content-Type: application/json" \
  -d '{"level": "ERROR", "message": "Test"}'

# Sentry'de görün: https://sentry.io/organizations/your-org

# Signup testini yap
POST /auth/register
{
  "email": "test@example.com",
  "password": "SecurePassword123!"
}

# E-posta geldi mi kontrol et
# PostHog'da signup event'ini gör
```

### 4. Production'a Deploy (15 dakika)

```bash
# Production secrets tamamen ayarlandıysa
git push origin main

# Health check
curl https://api.yourdomain.com/health

# API key al
POST https://api.yourdomain.com/auth/register
{
  "email": "your@email.com"
}

# İlk persona'yı satın al
POST /checkout/persona_socrates

# Entegrasyonları izle:
# - Sentry: https://sentry.io/organizations/your-org
# - PostHog: https://posthog.com/app
# - Resend: https://resend.com/logs
```

---

## 📊 Entegrasyon Durumu

| Entegrasyon | Durum | Kurulum | Test |
|---|---|---|---|
| **Sentry** | ✅ Kodlanmış | 5 min | 5 min |
| **PostHog** | ✅ Kodlanmış | 5 min | 5 min |
| **Resend** | ✅ Kodlanmış | 5 min | 5 min |
| **Supabase Storage** | ✅ Kodlanmış | 10 min | 10 min |
| **Vercel Secrets** | ✅ Rehber | 15 min | 5 min |

**Toplam Kurulum Süresi: ~1 saat**

---

## 🔐 Güvenlik Kontrol Listesi

- [ ] API anahtarları kod içinde DEĞİL (tümü environment variables)
- [ ] Vercel'de tüm secrets eklenmiş
- [ ] Staging'te test edilmiş
- [ ] SENTRY_DSN çalışıyor (test error gönderildi)
- [ ] POSTHOG_API_KEY geçerli (event capture çalışıyor)
- [ ] RESEND_API_KEY domain'i doğrulanmış
- [ ] STRIPE webhook secret doğru
- [ ] DATABASE_URL Production veritabanına işaret ediyor
- [ ] JWT_SECRET_KEY 32+ byte (openssl rand -hex 32)
- [ ] ENVIRONMENT=production ayarlanmış

---

## 📱 Endpoints (Test Etme)

### Herkese Açık
```bash
GET /health
GET /personas
GET /personas/{id}/profile
POST /auth/register
```

### API Key Gerekli (X-API-Key header)
```bash
GET /me
GET /me/purchases
GET /me/wallet
POST /checkout/{persona_id}
POST /v1/compile/{persona_id}
POST /uploads/avatar
POST /uploads/compiled-config/{persona_id}
DELETE /uploads/avatar
```

### Admin Endpointleri
```bash
GET /observability/metrics
GET /observability/health/deep
POST /observability/logs/collect
```

---

## 🐛 Sorun Çözme

### E-posta gelmiyorsa
```bash
1. RESEND_API_KEY kontrol et (re_ ile başlıyor mı?)
2. FROM_EMAIL domain'i doğrulanmış mı?
3. Spam klasörü kontrol et
4. Resend dashboard'dan logs'u kontrol et
```

### Sentry hata capture etmiyorsa
```bash
1. SENTRY_DSN kontrol et (https://... format)
2. ENVIRONMENT=production ayarlanmış mı?
3. Test error gönder (curl ile)
4. Sentry dashboard'a git, latest events kontrol et
```

### PostHog event görünmüyorsa
```bash
1. POSTHOG_API_KEY kontrol et (phc_ ile başlıyor mı?)
2. POSTHOG_HOST doğru mu? (eu.posthog.com veya us.posthog.com)
3. PostHog dashboard'ta Events → Recent section'ı kontrol et
```

### Dosya upload başarısız
```bash
1. SUPABASE_URL ve SUPABASE_SERVICE_ROLE_KEY kontrol et
2. Storage buckets oluşturulmuş mı?
3. GET /uploads/status endpoint'ini kontrol et
4. Supabase dashboard'dan bucket permissions kontrol et
```

---

## 📈 Monitoring Sonrası

### Günlük Check
```
□ Sentry error rate < 5%
□ PostHog events coming in
□ E-postalalar gönderiliyor
□ API response time < 500ms (p95)
□ Database connection pool healthy
```

### Haftalık Check
```
□ Revenue tracking PostHog'da görülüyor mu?
□ Referral codes çalışıyor mu?
□ Compilation success rate > 95%?
□ Storage bucket size kontrol et
```

### Aylık Check
```
□ Sentry subscription quota kontrol
□ PostHog event quota kontrol
□ Resend email quota kontrol
□ Database backup alındı mı?
□ Secrets rotation zamanı mı?
```

---

## 🔄 Secret Rotation (Üç Ayda Bir)

```bash
# 1. Yeni secret oluştur
openssl rand -hex 32  # JWT_SECRET_KEY için

# 2. Vercel'de YENI secret'i ekle (eski yanında)
VERCEL: JWT_SECRET_KEY=<yeni_key>

# 3. Deploy et
git push origin main

# 4. 24-48 saat bekle (cache temizlenmesi için)

# 5. Eski secret'i sil
VERCEL: Remove old JWT_SECRET_KEY

# 6. Son deploy
git push origin main
```

---

## 📞 Destek ve Dokümantasyon

Detaylı bilgi için şu dosyaları oku:
- **INTEGRATIONS.md** - Tüm entegrasyonların detaylı kurulum rehberi
- **INTEGRATION_STATUS.md** - Bu oturumda yapılan değişikliklerin özeti
- **DEPLOYMENT_CHECKLIST.md** - Production deployment adımları
- **PERFORMANCE_ANALYSIS.md** - Performans baseline ve optimizasyon
- **.env.example** - Tüm environment variables

---

## ✅ Başlatma Kontrol Listesi

### Kod Hazır ✅
- [x] Sentry entegrasyonu
- [x] PostHog entegrasyonu
- [x] Supabase Storage entegrasyonu
- [x] Email templates
- [x] Hata handling
- [x] Dosya validation

### Harici Hizmetler Kurulmuş ⏳
- [ ] Sentry project oluşturuldu
- [ ] PostHog project oluşturuldu
- [ ] Resend configured
- [ ] Supabase buckets oluşturuldu
- [ ] Stripe webhook yapılandırıldı

### Vercel Secrets Eklendi ⏳
- [ ] SENTRY_DSN
- [ ] POSTHOG_API_KEY
- [ ] RESEND_API_KEY
- [ ] STRIPE_SECRET_KEY
- [ ] DATABASE_URL
- [ ] JWT_SECRET_KEY
- [ ] SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY

### Staging Test Edildi ⏳
- [ ] Health endpoint çalışıyor
- [ ] E-posta gönderiliyor
- [ ] Hata tracking çalışıyor
- [ ] Events capture ediliyor
- [ ] Dosya upload çalışıyor
- [ ] Compilation başarılı

### Production Deploy ⏳
- [ ] Staging tests passed
- [ ] Tüm secrets eklendi
- [ ] Health check başarılı
- [ ] Monitoring dashboards açık

---

## 🎯 Özet

| Aşama | Zaman | Durum |
|---|---|---|
| Harici hizmetleri kur | 30 min | ⏳ User yapacak |
| Vercel secrets ekle | 15 min | ⏳ User yapacak |
| Staging test et | 30 min | ⏳ User yapacak |
| Production deploy | 15 min | ⏳ User yapacak |
| **TOPLAM** | **90 min** | ⏳ |

---

**Hepsi hazır! Sadece harici hizmetleri kur ve secrets'leri ekle.**

Sorular varsa, INTEGRATIONS.md ve INTEGRATION_STATUS.md'ye bak.

🚀 **İyi şanslar!**
