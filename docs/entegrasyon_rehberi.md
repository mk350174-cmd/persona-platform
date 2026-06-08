# Claude Code — Tam Entegrasyon Rehberi & Katalogu

> Token optimizasyonu ve maksimum verimlilik için hazırlanmış kapsamlı rehber.

---

## İçindekiler
1. [Strateji: Neden Çoklu Model?](#strateji)
2. [AI Model Entegrasyonları](#ai-modeller)
3. [MCP Server Katalogu](#mcp-katalog)
4. [Token Optimizasyon Tablosu](#token-optimizasyon)
5. [Tavsiye Edilen Kurulum Setleri](#kurulum-setleri)
6. [Kurulum Komutları](#kurulum)

---

## 1. Strateji: Neden Çoklu Model? {#strateji}

Claude Code'u tek başına kullanmak yerine, her modelin güçlü olduğu alanda kullanarak hem maliyet hem hız kazanırsın.

```
Pahalı / Karmaşık    →  Claude Code (orkestratör)
Uzun dosya / web     →  Gemini CLI
Basit boilerplate    →  OpenAI Codex
Ücretsiz / lokal     →  Ollama
Hız gereken          →  Groq
```

---

## 2. AI Model Entegrasyonları {#ai-modeller}

### 2.1 Doğrudan CLI Entegrasyonları

| Model | Güçlü Alan | Kurulum |
|-------|-----------|---------|
| **Gemini CLI** | 1M token context, web arama, uzun dosya okuma | `npm install -g @google/gemini-cli` |
| **OpenAI Codex** | Boilerplate üretimi, hızlı kod tamamlama | `npm install -g @openai/codex` |
| **GitHub Copilot CLI** | Git workflow entegrasyonu | `npm install -g @githubnext/github-copilot-cli` |

### 2.2 Ollama ile Ücretsiz Lokal Modeller

> Ocak 2026'da Ollama, Anthropic Messages API desteği ekledi — Claude Code herhangi bir Ollama modeliyle doğrudan çalışabiliyor.

```bash
# Ollama kur
curl -fsSL https://ollama.com/install.sh | sh

# Model çek
ollama pull qwen2.5-coder:32b   # En güçlü lokal kod modeli
ollama pull glm-4.7-flash        # Hızlı, 128K context, tool calling
ollama pull deepseek-coder       # Kod üretimi
ollama pull gemma3               # Genel amaç
```

**Claude Code'a bağla:**
```bash
export ANTHROPIC_BASE_URL=http://localhost:11434
export ANTHROPIC_API_KEY=""
claude --model ollama/qwen2.5-coder:32b
```

### 2.3 Bifrost Gateway ile (20+ Provider)

Tek bir gateway üzerinden tüm modellere erişim:

```bash
# Bifrost kur
npm install -g @maximai/bifrost-cli

# Model değiştir (mid-session)
/model openai/gpt-4o
/model groq/llama-3.3-70b
/model ollama/qwen2.5-coder:32b
/model google/gemini-2.5-pro
```

**Desteklenen providerlar:** Anthropic, OpenAI, AWS Bedrock, Google Vertex AI, Azure OpenAI, Groq, Mistral, Cohere, Ollama ve daha fazlası.

### 2.4 Token Optimizasyon Tablosu {#token-optimizasyon}

| Görev | Model | Neden |
|-------|-------|-------|
| Mimari karar, karmaşık logic | **Claude Code** | En iyi reasoning |
| Code review, refactor | **Claude Code** | Codebase'i tanıyor |
| Büyük dosya okuma (500+ satır) | **Gemini CLI** | 1M token context, ucuz |
| Web'den güncel bilgi | **Gemini CLI** | Arama özelliği |
| Basit CRUD / boilerplate | **Codex** | Hızlı ve ucuz |
| Ücretsiz / tekrarlayan görevler | **Ollama** | Sıfır maliyet |
| Hız gerektiren görevler | **Groq** | ~25 token/sn |

---

## 3. MCP Server Katalogu {#mcp-katalog}

### 🔧 Kod & Repo

| Server | Ne Yapar | Kurulum |
|--------|---------|---------|
| **GitHub MCP** | PR okuma, issue yönetimi, repo arama, otomatik katkı | `claude mcp add github` |
| **Git MCP** | Diff, log, blame, branch işlemleri | `claude mcp add git -- uvx mcp-server-git` |
| **Filesystem** | CWD dışındaki dosyalara erişim | `claude mcp add filesystem` |
| **Context7** | Güncel dokümantasyon çeker, halüsinasyonu azaltır | `claude mcp add context7` |

### 🗄️ Veritabanı

| Server | Ne Yapar | Kurulum |
|--------|---------|---------|
| **PostgreSQL** | DB'yi doğrudan sorgula | `claude mcp add postgres` |
| **SQLite** | Lokal DB işlemleri | `claude mcp add sqlite -- uvx mcp-server-sqlite` |
| **Supabase** | Full backend erişimi | `claude mcp add supabase` |

### 🌐 Web & Arama

| Server | Ne Yapar | Kurulum |
|--------|---------|---------|
| **Brave Search** | Web arama (Gemini yokken alternatif) | `claude mcp add brave-search` |
| **Fetch** | URL içeriği çekme | `claude mcp add fetch -- uvx mcp-server-fetch` |
| **Playwright** | Tarayıcı otomasyonu, E2E test | `claude mcp add playwright` |

### 📋 Proje Yönetimi

| Server | Ne Yapar | Kurulum |
|--------|---------|---------|
| **Linear** | Ticket yönetimi, sprint takibi | `claude mcp add linear` |
| **Notion** | Dokümantasyon okuma/yazma | `claude mcp add notion` |
| **Slack** | Kanal mesajları, bildirim gönderme | `claude mcp add slack` |
| **Zapier** | 1000+ uygulama bağlantısı | `claude mcp add zapier` |

### 🖥️ Infrastrüktür & Monitoring

| Server | Ne Yapar | Kurulum |
|--------|---------|---------|
| **Docker** | Container durumu, log yönetimi | `claude mcp add docker` |
| **Kubernetes** | Cluster sorguları, pod durumu | `claude mcp add kubernetes -- npx -y kubernetes-mcp-server` |
| **Sentry** | Hata takip verisini Claude'a getirir | `claude mcp add sentry` |
| **Datadog** | Production metrik ve alertler | `claude mcp add datadog` |

### 🧠 Reasoning & Hafıza

| Server | Ne Yapar | Kurulum |
|--------|---------|---------|
| **Memory** | Projeler arası kalıcı hafıza | `claude mcp add memory` |
| **Sequential Thinking** | Karmaşık problem çözme adımları | `claude mcp add sequential-thinking` |

### 🎨 Tasarım

| Server | Ne Yapar | Kurulum |
|--------|---------|---------|
| **Figma** | Design-to-code workflow | `npx @composio/mcp@latest setup figma --client claude` |

---

## 4. Tavsiye Edilen Kurulum Setleri {#kurulum-setleri}

> ⚠️ **Kural:** 4-6 server seç, fazlası tool budget'ını doldurup token israfına yol açar.

### Web / Full-Stack Geliştirici
```
✅ GitHub MCP
✅ PostgreSQL veya Supabase
✅ Playwright
✅ Context7
✅ Sentry
+ Gemini CLI (uzun dosyalar için)
+ Ollama (boilerplate için)
```

### API / Backend Geliştirici
```
✅ GitHub MCP
✅ PostgreSQL
✅ Docker
✅ Sentry veya Datadog
✅ Context7
+ Groq (hızlı testler için)
```

### Solo Geliştirici / Freelancer
```
✅ GitHub MCP
✅ SQLite
✅ Brave Search veya Fetch
✅ Memory
+ Ollama (maliyet sıfırlamak için)
+ Gemini CLI (uzun dosyalar için)
```

### Takım / Kurumsal
```
✅ GitHub MCP
✅ Linear
✅ Slack
✅ PostgreSQL
✅ Sentry
✅ Notion
+ Bifrost Gateway (çoklu model yönetimi)
```

---

## 5. Kurulum Referansı {#kurulum}

### MCP Server Ekleme (Genel Format)
```bash
# npm tabanlı serverlar
claude mcp add <isim> -- npx -y <paket>

# Python tabanlı serverlar
claude mcp add <isim> -- uvx <paket>

# Doğrudan
claude mcp add <isim>
```

### .claude/mcp.json Örneği
```json
{
  "mcpServers": {
    "gemini": {
      "command": "npx",
      "args": ["@google/gemini-cli", "--mcp"],
      "env": { "GEMINI_API_KEY": "YOUR_KEY" }
    },
    "codex": {
      "command": "npx",
      "args": ["@openai/codex", "--mcp"],
      "env": { "OPENAI_API_KEY": "YOUR_KEY" }
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_TOKEN": "YOUR_TOKEN" }
    },
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/mydb"]
    }
  }
}
```

### Pipeline Örneği (Token Optimizasyonu)
```
1. Gemini CLI  → 1000 satırlık dosyayı oku ve özetle
2. Claude Code → Mimari kararı ver
3. Codex       → Boilerplate endpoint'leri yaz
4. Claude Code → Kritik business logic'i yaz
5. Sentry MCP  → Hataları takip et
```

---

## Hızlı Referans Kartı

```
UCUZ/ÜCRETSİZ     →  Ollama (lokal)
HIZLI             →  Groq
UZUN CONTEXT      →  Gemini CLI (1M token)
WEB ARAMA         →  Gemini CLI veya Brave Search MCP
KOD ÜRETİMİ       →  Codex
REPO YÖNETİMİ     →  GitHub MCP
VERİTABANI        →  PostgreSQL / Supabase MCP
HATA TAKİP        →  Sentry MCP
TARAYICI          →  Playwright MCP
DOKÜMANTASYON     →  Context7 MCP
```

---

*Son güncelleme: Haziran 2026 | Claude Code ekosistemi hızla gelişiyor, MCP kataloğunu düzenli kontrol et: https://code.claude.com/docs/en/mcp*
