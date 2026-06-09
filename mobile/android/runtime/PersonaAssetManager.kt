package com.persona.needle

import android.content.Context
import org.json.JSONObject
import java.io.File

/**
 * PersonaAssetManager — discover and stage persona bundles shipped in the APK's
 * assets/personas/ tree. GGUF models must be copied out of assets onto the filesystem
 * (llama.cpp can't mmap from the asset manager), which [extractToCache] handles.
 */
class PersonaAssetManager(private val context: Context) {

    private val root = "personas"

    fun listAvailablePersonas(): List<PersonaMetadata> {
        val ids = context.assets.list(root)?.toList() ?: emptyList()
        return ids.mapNotNull { id -> runCatching { getPersonaMetadata(id) }.getOrNull() }
    }

    fun getPersonaMetadata(personaId: String): PersonaMetadata {
        val text = context.assets.open("$root/$personaId/manifest.json")
            .bufferedReader().use { it.readText() }
        val json = JSONObject(text)
        val ceid = json.optJSONObject("ceid_baseline") ?: JSONObject()
        val baseline = ceid.keys().asSequence()
            .associateWith { ceid.optDouble(it, 0.0).toFloat() }
        return PersonaMetadata(
            personaId = json.optString("persona_id", personaId),
            version = json.optString("version", "1.0"),
            // Python manifest uses snake_case; map total_size_mb / untrained → Kotlin fields.
            sizeMb = json.optDouble("total_size_mb", 0.0).toFloat(),
            isUntrained = json.optBoolean("untrained", true),
            ceidBaseline = baseline,
            domain = (json.optJSONObject("ceid_baseline")?.optString("domain")) ?: "",
            components = emptyMap()
        )
    }

    fun extractToCache(personaId: String): String {
        val outDir = File(context.cacheDir, "$root/$personaId").apply { mkdirs() }
        val gguf = File(outDir, "model.gguf")
        if (!gguf.exists()) {
            // find the .gguf inside assets/personas/{id}/ and copy it out
            val name = context.assets.list("$root/$personaId")
                ?.firstOrNull { it.endsWith(".gguf") } ?: "model.gguf"
            context.assets.open("$root/$personaId/$name").use { input ->
                gguf.outputStream().use { input.copyTo(it) }
            }
        }
        return gguf.absolutePath
    }

    fun getCacheSize(): Long {
        val dir = File(context.cacheDir, root)
        return dir.walkTopDown().filter { it.isFile }.sumOf { it.length() }
    }

    fun clearCache(personaId: String? = null) {
        val dir = if (personaId == null) File(context.cacheDir, root)
        else File(context.cacheDir, "$root/$personaId")
        dir.deleteRecursively()
    }
}

data class PersonaMetadata(
    val personaId: String,
    val version: String,
    val sizeMb: Float,
    val isUntrained: Boolean,
    val ceidBaseline: Map<String, Float>,
    val domain: String,
    val components: Map<String, ComponentInfo>
)

data class ComponentInfo(
    val path: String,
    val sizeMb: Float
)
