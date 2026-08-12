# "Google/GitHub ile Giriş Yap" Nasıl Kurulur? (T2-008)

## Önce: bu ne işe yarıyor?

Şu an persona-platform'da kullanıcılar sadece e-posta + şifre ile kayıt
oluyor (`/auth/register`). "Google ile giriş yap" / "GitHub ile giriş yap"
butonu eklemek istiyorsanız — kullanıcı kendi Google/GitHub hesabıyla tek
tıkla giriş yapsın, ayrı bir şifre hatırlamasın — buna **OAuth2** deniyor.

Bunu çalıştırmak için **Google'ın ve GitHub'ın kendi sistemlerine** gidip
"benim uygulamam var, ona giriş izni ver" demeniz gerekiyor. Bu, ben
(Claude Code) yapamayacağım bir adım — çünkü bu sizin hesabınızda, sizin
adınıza bir "uygulama kaydı" oluşturmak demek. Ben kodu yazarım, ama bu
kaydı sizin yapmanız gerekiyor.

## Adım adım: Google için

1. https://console.cloud.google.com/ adresine gidin, Google hesabınızla
   giriş yapın.
2. Üstte "Yeni Proje" oluşturun (örn. "Persona Platform").
3. Sol menüden **APIs & Services → OAuth consent screen**'e gidin.
   - "External" seçin (herkese açık bir uygulama).
   - Uygulama adı, destek e-postası gibi basit bilgileri doldurun.
4. Sol menüden **APIs & Services → Credentials**'a gidin.
   - "Create Credentials" → "OAuth client ID" seçin.
   - Uygulama tipi: "Web application".
   - **Authorized redirect URI** alanına şunu yazın (geliştirme için):
     `http://localhost:8000/auth/google/callback`
     (canlıya çıktığınızda gerçek domain'inizle güncellersiniz, örn.
     `https://persona-platform.com/auth/google/callback`)
5. "Create" dediğinizde size iki şey verir:
   - **Client ID** (uzun bir metin, gizli değil)
   - **Client Secret** (bu gerçekten gizli — parola gibi düşünün)

## Adım adım: GitHub için

1. https://github.com/settings/developers adresine gidin.
2. "OAuth Apps" → "New OAuth App".
3. Şu bilgileri doldurun:
   - Application name: "Persona Platform"
   - Homepage URL: `http://localhost:8000` (geliştirme) veya gerçek domain
   - **Authorization callback URL:** `http://localhost:8000/auth/github/callback`
4. "Register application" dediğinizde bir **Client ID** görürsünüz.
5. "Generate a new client secret" butonuna basın — bir **Client Secret**
   verir (sadece bir kez gösterilir, kaydedin).

## Bu bilgileri bana nasıl vermelisiniz?

**Client ID ve Client Secret'ı doğrudan sohbete yapıştırmayın** — bunlar
parola niteliğinde. Bunun yerine iki yol var:

1. **Şimdilik hiç vermeyin** — ben kodu, bu değerleri ortam değişkeninden
   (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GITHUB_CLIENT_ID`,
   `GITHUB_CLIENT_SECRET`) okuyacak şekilde yazarım (aşağıda yaptım).
   Siz bu değerleri gerçek sunucunuzda (Render/Railway/Fly.io/kendi
   sunucunuz — nereye deploy ederseniz) "Environment Variables" ayarına
   girdiğinizde her şey otomatik çalışır. Kod hazır bekler.
2. Test etmek isterseniz, bu değerleri kendi bilgisayarınızda
   `persona-platform/.env` dosyasına (bu dosya `.gitignore`'da, asla
   git'e gitmez) yazıp orada tutarsınız.

## NVIDIA anahtarınız için not

Bu arada verdiğiniz NVIDIA API anahtarını sohbete yapıştırdınız — bunu
kullandım (aşağıdaki NVIDIA entegrasyonuna bakın) ama şunu bilmenizi
isterim: bu anahtar artık bu konuşma geçmişinde düz metin olarak duruyor.
Ciddi bir risk değil (kod'a hiçbir yerde commit edilmedi, sadece ortam
değişkeni olarak kullanıldı) ama ileride, özellikle canlıya çıkmadan önce,
NVIDIA'nın build.nvidia.com panelinden bu anahtarı iptal edip yenisini
almanız iyi bir alışkanlık olur — parola sıfırlamaya benzer, zorunlu
değil ama önerilir.
