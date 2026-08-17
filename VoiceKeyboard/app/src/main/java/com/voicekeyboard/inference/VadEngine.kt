package com.voicekeyboard.inference

import android.content.Context
import android.util.Log
import java.io.File
import java.nio.FloatBuffer

/**
 * Lightweight Voice Activity Detection using Silero VAD.
 * Used to gate Whisper inference: only run transcription when voice is detected.
 */
class VadEngine(private val context: Context) {

    private var onnxSession: ai.onnxruntime.OrtSession? = null
    private var onnxEnv: ai.onnxruntime.OrtEnvironment? = null

    // Silero hidden state [2, 1, 64]
    private var hState = FloatArray(128)
    private var cState = FloatArray(128)

    private val windowSize = 512   // 32 ms at 16 kHz
    val threshold = 0.5f

    fun load(vadModelFile: File) {
        if (!vadModelFile.exists()) {
            Log.w(TAG, "VAD model not found at ${vadModelFile.path}; VAD disabled")
            return
        }
        onnxEnv = ai.onnxruntime.OrtEnvironment.getEnvironment()
        val opts = ai.onnxruntime.OrtSession.SessionOptions().apply {
            setIntraOpNumThreads(1)
        }
        onnxSession = onnxEnv!!.createSession(vadModelFile.absolutePath, opts)
        resetState()
        Log.i(TAG, "VAD loaded")
    }

    fun isVoice(chunk: FloatArray): Boolean {
        val session = onnxSession ?: return true   // no VAD → always pass through
        val env = onnxEnv ?: return true
        return try {
            val padded = FloatArray(windowSize)
            System.arraycopy(chunk, 0, padded, 0, minOf(chunk.size, windowSize))

            val audioTensor = ai.onnxruntime.OnnxTensor.createTensor(
                env, FloatBuffer.wrap(padded), longArrayOf(1, windowSize.toLong())
            )
            val srTensor = ai.onnxruntime.OnnxTensor.createTensor(
                env, longArrayOf(16000L), longArrayOf(1)
            )
            val hTensor = ai.onnxruntime.OnnxTensor.createTensor(
                env, FloatBuffer.wrap(hState), longArrayOf(2, 1, 64)
            )
            val cTensor = ai.onnxruntime.OnnxTensor.createTensor(
                env, FloatBuffer.wrap(cState), longArrayOf(2, 1, 64)
            )

            val result = session.run(
                mapOf("input" to audioTensor, "sr" to srTensor, "h" to hTensor, "c" to cTensor)
            )
            val prob = (result[0].value as Array<*>)[0] as Float
            hState = (result[1].value as Array<*>).flatten().map { (it as Float) }.toFloatArray()
            cState = (result[2].value as Array<*>).flatten().map { (it as Float) }.toFloatArray()

            audioTensor.close(); srTensor.close(); hTensor.close(); cTensor.close()
            result.close()
            prob >= threshold
        } catch (e: Exception) {
            Log.w(TAG, "VAD inference error: ${e.message}")
            true
        }
    }

    fun resetState() {
        hState = FloatArray(128)
        cState = FloatArray(128)
    }

    fun unload() {
        onnxSession?.close(); onnxSession = null
        onnxEnv?.close(); onnxEnv = null
    }

    companion object {
        private const val TAG = "VadEngine"
    }
}
