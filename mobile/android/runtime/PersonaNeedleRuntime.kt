package com.persona.needle

import android.content.Context

/**
 * PersonaNeedleRuntime — loads INT4 GGUF persona bundles and runs CEID / drift / voice
 * on-device via the llama.cpp Android JNI. One process can hold several personas; call
 * [unloadPersona] to free memory.
 *
 * Assets are expected under assets/personas/{personaId}/ (model.gguf + klayer.json +
 * manifest.json), produced by needle/finetune/export + needle/pipeline (see android/README.md).
 *
 * NOTE: this is integration scaffold — the native llama.cpp calls are marked TODO and a
 * binding (e.g. com.llama.llamacpp) must be wired in to run inference.
 */
class PersonaNeedleRuntime(
    private val context: Context,
    private val assetsPath: String = "personas"
) {
    private val loadedPersonas = mutableMapOf<String, PersonaHandle>()
    private val assets = PersonaAssetManager(context)

    fun loadPersona(personaId: String): PersonaHandle {
        loadedPersonas[personaId]?.let { return it }
        val meta = assets.getPersonaMetadata(personaId)
        val modelPath = assets.extractToCache(personaId)  // GGUF must live on the filesystem
        // TODO: val ctx = LlamaAndroid.loadModel(modelPath)  // llama.cpp JNI
        val handle = PersonaHandle(
            personaId = personaId,
            modelPath = modelPath,
            kLayerVector = emptyMap(),                     // TODO: read klayer.json
            ceidBaseline = meta.ceidBaseline,
            isUntrained = meta.isUntrained
        )
        loadedPersonas[personaId] = handle
        return handle
    }

    fun measureCeid(personaId: String, conversation: String): CeidResult {
        val handle = loadedPersonas[personaId] ?: loadPersona(personaId)
        // TODO: val json = LlamaAndroid.infer(handle.ctx, ceidPrompt(handle, conversation))
        // Parse {"C":..,"E":..,"I":..,"D":..} from the model output.
        return CeidResult(0f, 0f, 0f, 0f, isUntrained = handle.isUntrained)
    }

    fun detectDrift(personaId: String, conversation: String): DriftResult {
        val handle = loadedPersonas[personaId] ?: loadPersona(personaId)
        // TODO: parse {"drift":bool,"score":float} from the drift head output.
        return DriftResult(drift = false, score = 0f, warning = null)
    }

    fun generateVoice(personaId: String, prompt: String, maxTokens: Int = 256): String {
        val handle = loadedPersonas[personaId] ?: loadPersona(personaId)
        // TODO: return LlamaAndroid.generate(handle.ctx, voicePrompt(handle, prompt), maxTokens)
        return ""
    }

    fun unloadPersona(personaId: String) {
        loadedPersonas.remove(personaId)
        // TODO: LlamaAndroid.freeModel(handle.ctx)
    }

    fun getLoadedPersonas(): List<String> = loadedPersonas.keys.toList()
}

data class PersonaHandle(
    val personaId: String,
    val modelPath: String,
    val kLayerVector: Map<String, Float>,
    val ceidBaseline: Map<String, Float>,
    val isUntrained: Boolean
)

data class CeidResult(
    val C: Float, val E: Float,
    val I: Float, val D: Float,
    val isUntrained: Boolean
)

data class DriftResult(
    val drift: Boolean,
    val score: Float,
    val warning: String?
)
