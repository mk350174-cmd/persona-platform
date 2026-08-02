# ADR 0002 — persona_mcp Paylaşım Kararı + Submodule Stratejisi (T3-005/T3-007)

**Durum:** Kabul edildi (Claude Code mimari kararı, CLAUDE.md "Model Seçim
Kuralları" — mimari kararlar Claude Code'un sorumluluğunda; iş/hesap
kararı olmadığı için kullanıcı onayı gerektirmedi, ADR 0001'in kapsamına
ek).

## Bağlam

`persona_math/`, `needle/`, `persona_mcp/` iki repoda da var
(`mk350174-cmd/Persona` ve `mk350174-cmd/persona-platform`), şu anda **elle
senkronize** ediliyor. Bu turda doğrulandı: `needle/training/dataset/
builder.py` iki repo arasında zaten yeniden çatallanmış (kozmetik ama
gerçek bir fark — değişken adlandırma, muhtemelen iki repoda ayrı ayrı
çalıştırılan ruff/format araçlarından), `TEACHERS.md` sadece platform'da
var. Bu, elle senkronizasyonun beklendiği gibi drift'e yol açtığının somut
kanıtı.

## T3-005 — persona_mcp paylaşım kararı

**Karar:** `persona_mcp` (ve `persona_math`, `needle`) **Persona reposu
kanonik kaynak** olmaya devam eder. persona-platform bunları **tüketir**,
bağımsız olarak geliştirmez. Bu zaten ADR 0001 T2-003'ün zımni varsayımıydı
("eski `api/needle_service.py` deseni **referans alınır**, kopyalanmaz")
— burada açıkça karar olarak kayıt altına alınıyor.

## T3-007 — Submodule stratejisi

**Karar: Şimdilik submodule'e geçilmiyor, ama nedeni ve tetikleyici koşul
kayıt altında.**

Gerekçe — neden şimdi değil:
- Git submodule iş akışına ek karmaşıklık ekliyor (detached HEAD,
  `git submodule update --init`'i unutma riski, CI'da ekstra checkout adımı)
  ve şu anda **tek kişi** (kullanıcı + Claude Code oturumları) bu kodu
  değiştiriyor — submodule'ün asıl faydası (çok-repo, çok-katkıcı senaryosunda
  versiyon tutarlılığı) henüz devrede değil.
- Kaggle eğitim hattı henüz aktif değil (bloke) — `needle/` üzerinde
  gerçek, sık değişiklik trafiği henüz yok. Trafik arttığında maliyet/fayda
  dengesi değişir.

Tetikleyici koşul (bundan sonra submodule'e geçilmeli):
- `needle/`, `persona_math/`, veya `persona_mcp/` üzerinde **iki repoda
  bağımsız commit** tekrar tespit edilirse (bu turda olduğu gibi), VEYA
- Kaggle eğitim hattı aktif hale gelip `needle/` üzerinde haftalık birden
  fazla değişiklik olmaya başlarsa.

Bu koşullardan biri gerçekleştiğinde: Persona reposunu kanonik tutup
persona-platform'da `git submodule add <persona-repo-url> vendor/persona-core`
şeklinde eklenmeli, mevcut `needle/persona_math/persona_mcp` dizinleri
kaldırılıp import path'leri güncellenmelidir. Bu, ayrı bir ADR (0003)
gerektirecek kadar büyük bir değişiklik.

## Ara-dönem disiplini (submodule'e geçene kadar)

Her iki repoda `needle/persona_math/persona_mcp` değişikliği yapan oturum,
değişikliği **diğer repoya da elle taşımalı** (bu oturumda `builder.py`/
`TEACHERS.md` farkı bulundu ama kapsam dışı bırakıldı — Faz 9 kapsamı
mimari karar, kod senkronizasyonu değil; bir sonraki oturumda ele alınmalı).
