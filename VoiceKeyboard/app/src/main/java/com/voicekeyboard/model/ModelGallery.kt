package com.voicekeyboard.model

import android.content.Context
import android.content.SharedPreferences
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import java.io.File

class ModelGallery(private val context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences("model_gallery", Context.MODE_PRIVATE)
    private val gson = Gson()
    private val modelDir: File = File(context.filesDir, "models").also { it.mkdirs() }

    // Curated edge gallery — all run fully on-device
    val catalog: List<VoiceModel> = listOf(
        VoiceModel(
            id = "whisper_tiny_en_tflite",
            name = "Whisper Tiny (EN)",
            description = "OpenAI Whisper Tiny quantised to INT8 via TFLite. Best for low-RAM devices.",
            size = ModelSize.TINY,
            backend = InferenceBackend.TFLITE,
            fileName = "whisper_tiny_en_int8.tflite",
            sampleRate = 16000,
            language = "en",
            isQuantized = true,
            fileSizeMb = 39f,
            wer = 0.12f,
            rtf = 0.08f
        ),
        VoiceModel(
            id = "whisper_base_en_tflite",
            name = "Whisper Base (EN)",
            description = "OpenAI Whisper Base quantised INT8. Good balance of quality and speed.",
            size = ModelSize.BASE,
            backend = InferenceBackend.TFLITE,
            fileName = "whisper_base_en_int8.tflite",
            sampleRate = 16000,
            language = "en",
            isQuantized = true,
            fileSizeMb = 74f,
            wer = 0.08f,
            rtf = 0.15f
        ),
        VoiceModel(
            id = "whisper_tiny_multilingual_onnx",
            name = "Whisper Tiny Multi",
            description = "Multilingual Whisper Tiny via ONNX Runtime. Supports 99 languages.",
            size = ModelSize.TINY,
            backend = InferenceBackend.ONNX,
            fileName = "whisper_tiny_multilingual.onnx",
            sampleRate = 16000,
            language = "multi",
            isQuantized = true,
            fileSizeMb = 44f,
            wer = 0.15f,
            rtf = 0.10f
        ),
        VoiceModel(
            id = "whisper_base_multilingual_onnx",
            name = "Whisper Base Multi",
            description = "Multilingual Whisper Base via ONNX Runtime. High-quality, wider language support.",
            size = ModelSize.BASE,
            backend = InferenceBackend.ONNX,
            fileName = "whisper_base_multilingual.onnx",
            sampleRate = 16000,
            language = "multi",
            isQuantized = true,
            fileSizeMb = 80f,
            wer = 0.09f,
            rtf = 0.20f
        ),
        VoiceModel(
            id = "silero_vad_v4_onnx",
            name = "Silero VAD v4",
            description = "Voice Activity Detection only — ultra-light gating model used alongside Whisper.",
            size = ModelSize.TINY,
            backend = InferenceBackend.ONNX,
            fileName = "silero_vad_v4.onnx",
            sampleRate = 16000,
            language = "multi",
            isQuantized = false,
            fileSizeMb = 1.8f,
            wer = 0.0f,
            rtf = 0.01f
        )
    )

    private var _activeModelId: String
        get() = prefs.getString(KEY_ACTIVE_MODEL, catalog.first().id) ?: catalog.first().id
        set(v) = prefs.edit().putString(KEY_ACTIVE_MODEL, v).apply()

    val activeModel: VoiceModel
        get() = catalog.firstOrNull { it.id == _activeModelId } ?: catalog.first()

    fun setActiveModel(model: VoiceModel) {
        _activeModelId = model.id
    }

    fun isModelDownloaded(model: VoiceModel): Boolean =
        File(modelDir, model.fileName).exists()

    fun modelFile(model: VoiceModel): File = File(modelDir, model.fileName)

    fun saveDownloadedState(model: VoiceModel, downloaded: Boolean) {
        val key = "downloaded_${model.id}"
        prefs.edit().putBoolean(key, downloaded).apply()
    }

    fun enrichedCatalog(): List<VoiceModel> = catalog.map { m ->
        m.copy(
            isDownloaded = isModelDownloaded(m),
            isActive = m.id == _activeModelId
        )
    }

    companion object {
        private const val KEY_ACTIVE_MODEL = "active_model_id"
    }
}
