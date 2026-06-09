package com.persona.needle

/**
 * McpBridge — sends on-device results to the platform backend over HTTP (via [ApiClient]),
 * which runs PersonaNeedle and persists to persona_mcp/Logseq. This replaces the previous
 * direct WebSocket-to-Python path:
 *
 *     Android -> ApiClient(HTTP) -> Platform backend (FastAPI) -> PersonaNeedle -> persona_mcp -> Logseq
 *
 * Calls are retried up to [maxRetries] times with exponential backoff.
 */
class McpBridge(
    private val runtime: PersonaNeedleRuntime,
    private val serverUrl: String = "http://10.0.2.2:8000/api/v1",   // platform backend (emulator)
    private val maxRetries: Int = 3
) {
    private val api = ApiClient(serverUrl)

    private fun <T> withRetry(block: () -> T): T {
        var last: Exception? = null
        for (attempt in 0 until maxRetries) {
            try {
                return block()
            } catch (e: Exception) {
                last = e
                if (attempt < maxRetries - 1) {
                    Thread.sleep(1000L shl attempt)   // 1s, 2s, 4s
                }
            }
        }
        throw last ?: RuntimeException("McpBridge: request failed")
    }

    /** Measure CEID on the backend (which logs it to persona_mcp/Logseq). */
    fun syncCeidToServer(personaId: String, conversation: String): CeidResult =
        withRetry { api.measureCeid(personaId, conversation) }

    /** Detect drift on the backend (logs a drift event if found). */
    fun syncDriftToServer(personaId: String, conversation: String): DriftResult =
        withRetry { api.detectDrift(personaId, conversation) }

    fun requestPersonaProfile(personaId: String): String =
        withRetry { api.getPersonaProfile(personaId) }

    fun generateVoice(personaId: String, prompt: String): String =
        withRetry { api.generateVoice(personaId, prompt) }
}
