package com.persona.needle

import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.WebSocket
import okhttp3.WebSocketListener

/**
 * McpBridge — WebSocket bridge from the Android runtime to the Python persona_mcp server,
 * which persists results to Logseq. The on-device model produces CEID / drift; this ships
 * them to the server (Android → McpBridge → persona_mcp → Logseq).
 *
 * Start the server with:  python -m persona_mcp.server --port 8765
 */
class McpBridge(
    private val runtime: PersonaNeedleRuntime,
    private val serverUrl: String = "http://localhost:8765"
) {
    private val client = OkHttpClient()
    private var socket: WebSocket? = null

    fun connect(): Boolean {
        val wsUrl = serverUrl.replace("http://", "ws://").replace("https://", "wss://")
        val request = Request.Builder().url("$wsUrl/ws").build()
        socket = client.newWebSocket(request, object : WebSocketListener() {})
        return socket != null
    }

    fun syncCeidToServer(personaId: String, result: CeidResult) {
        val payload = """
            {"tool":"measure_persona_ceid","persona_id":"$personaId",
             "ceid":{"C":${result.C},"E":${result.E},"I":${result.I},"D":${result.D}},
             "untrained":${result.isUntrained}}
        """.trimIndent()
        socket?.send(payload)
    }

    fun syncDriftToServer(personaId: String, result: DriftResult) {
        val payload = """
            {"tool":"detect_drift","persona_id":"$personaId",
             "drift":${result.drift},"score":${result.score}}
        """.trimIndent()
        socket?.send(payload)
    }

    fun requestPersonaProfile(personaId: String): String {
        // MCP get_persona_profile over HTTP; returns the JSON profile as a string.
        val request = Request.Builder()
            .url("$serverUrl/tool/get_persona_profile?persona_id=$personaId")
            .build()
        client.newCall(request).execute().use { resp ->
            return resp.body?.string() ?: "{}"
        }
    }

    fun close() {
        socket?.close(1000, "bye")
    }
}
