package com.voicekeyboard.model

import com.google.gson.annotations.SerializedName

enum class InferenceBackend { TFLITE, ONNX }

enum class ModelSize(val displayName: String, val ramMb: Int) {
    TINY("Tiny", 40),
    BASE("Base", 80),
    SMALL("Small", 250),
    MEDIUM("Medium", 800)
}

data class VoiceModel(
    @SerializedName("id") val id: String,
    @SerializedName("name") val name: String,
    @SerializedName("description") val description: String,
    @SerializedName("size") val size: ModelSize,
    @SerializedName("backend") val backend: InferenceBackend,
    @SerializedName("fileName") val fileName: String,
    @SerializedName("sampleRate") val sampleRate: Int = 16000,
    @SerializedName("language") val language: String = "en",
    @SerializedName("isQuantized") val isQuantized: Boolean = true,
    @SerializedName("fileSizeMb") val fileSizeMb: Float,
    @SerializedName("wer") val wer: Float,              // word-error rate lower = better
    @SerializedName("rtf") val rtf: Float,              // real-time factor lower = faster
    @SerializedName("isDownloaded") var isDownloaded: Boolean = false,
    @SerializedName("isActive") var isActive: Boolean = false
) {
    val displaySize: String get() = "%.1f MB".format(fileSizeMb)
    val qualityLabel: String get() = when {
        wer < 0.05f -> "Excellent"
        wer < 0.10f -> "Good"
        wer < 0.20f -> "Fair"
        else -> "Draft"
    }
    val speedLabel: String get() = when {
        rtf < 0.1f -> "Ultra-fast"
        rtf < 0.3f -> "Fast"
        rtf < 0.7f -> "Moderate"
        else -> "Slow"
    }
}
