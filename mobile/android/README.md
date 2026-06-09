# PersonaNeedle — Android (platform-integrated)

Kotlin runtime for on-device persona evaluation, wired to the platform backend.

## Backend Bağlantısı
```
Android → ApiClient (HTTP) → Platform Backend (FastAPI, api/routers/persona_router.py)
                ↓
          PersonaNeedle
                ↓
          persona_mcp → Logseq
```

- `ApiClient.kt` — HTTP client for `/api/v1/personas/...` (ceid / drift / voice / profile).
- `McpBridge.kt` — retry wrapper (3 attempts, exp backoff) over `ApiClient`; pushes CEID/drift
  to the backend, which logs to persona_mcp/Logseq. (Replaces the old direct WebSocket path.)
- `PersonaNeedleRuntime.kt` / `PersonaAssetManager.kt` — on-device GGUF inference + asset
  management (for offline/edge mode; see `dependencies_note.txt`).

## Geliştirme
```bash
# Backend
uvicorn api.main:app --reload --port 8000

# Android baseUrl
#   emülatör     : http://10.0.2.2:8000/api/v1
#   gerçek cihaz : http://192.168.x.x:8000/api/v1
```

```kotlin
val bridge = McpBridge(PersonaNeedleRuntime(context), serverUrl = "http://10.0.2.2:8000/api/v1")
val ceid = bridge.syncCeidToServer("socrates", conversation)   // backend ölçer + Logseq'e yazar
val voice = bridge.generateVoice("socrates", "merhaba")
```

## Endpoints (backend)
| Method | Path | Ne |
|---|---|---|
| GET | `/api/v1/personas/` | persona listesi |
| GET | `/api/v1/personas/{id}/profile` | K-layer + referans CEID |
| POST | `/api/v1/personas/{id}/ceid` | CEID ölçümü |
| POST | `/api/v1/personas/{id}/drift` | drift tespiti |
| POST | `/api/v1/personas/{id}/voice` | persona sesiyle üretim |
| GET | `/api/v1/personas/{id}/history` | CEID/drift/konuşma geçmişi |

Bağımlılıklar: `dependencies_note.txt` (llama.cpp JNI, OkHttp, coroutines, ARM64).
