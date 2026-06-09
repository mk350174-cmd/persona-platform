package com.persona.needle

import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject

/**
 * ApiClient — HTTP bridge from the Android app to the platform FastAPI backend
 * (api/routers/persona_router.py, mounted at /api/v1). Replaces the old direct-WebSocket
 * path: the phone calls the backend, which runs PersonaNeedle (or the persona_math fallback)
 * and logs to persona_mcp.
 *
 *   emulator   -> baseUrl = "http://10.0.2.2:8000/api/v1"
 *   real device-> baseUrl = "http://<lan-ip>:8000/api/v1"
 */
class ApiClient(
    private val baseUrl: String = "http://localhost:8000/api/v1"
) {
    private val client = OkHttpClient()
    private val JSON = "application/json".toMediaType()

    fun measureCeid(personaId: String, conversation: String): CeidResult {
        val body = JSONObject().put("conversation", conversation).toString().toRequestBody(JSON)
        val request = Request.Builder()
            .url("$baseUrl/personas/$personaId/ceid")
            .post(body)
            .build()
        val response = client.newCall(request).execute()
        val json = JSONObject(response.body!!.string())
        return CeidResult(
            C = json.getDouble("C").toFloat(),
            E = json.getDouble("E").toFloat(),
            I = json.getDouble("I").toFloat(),
            D = json.getDouble("D").toFloat(),
            isUntrained = json.optBoolean("untrained", true)
        )
    }

    fun detectDrift(personaId: String, conversation: String): DriftResult {
        val body = JSONObject().put("conversation", conversation).toString().toRequestBody(JSON)
        val request = Request.Builder()
            .url("$baseUrl/personas/$personaId/drift")
            .post(body)
            .build()
        val response = client.newCall(request).execute()
        val json = JSONObject(response.body!!.string())
        return DriftResult(
            drift = json.optBoolean("drift", false),
            score = json.optDouble("score", 0.0).toFloat(),
            warning = if (json.isNull("warning")) null else json.optString("warning")
        )
    }

    fun generateVoice(personaId: String, prompt: String): String {
        val body = JSONObject().put("prompt", prompt).toString().toRequestBody(JSON)
        val request = Request.Builder()
            .url("$baseUrl/personas/$personaId/voice")
            .post(body)
            .build()
        val response = client.newCall(request).execute()
        val json = JSONObject(response.body!!.string())
        return json.optString("voice")
    }

    fun getPersonaProfile(personaId: String): String {
        val request = Request.Builder()
            .url("$baseUrl/personas/$personaId/profile")
            .get()
            .build()
        val response = client.newCall(request).execute()
        return response.body!!.string()
    }
}
