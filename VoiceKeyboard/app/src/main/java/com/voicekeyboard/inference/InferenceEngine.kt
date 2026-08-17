package com.voicekeyboard.inference

import android.content.Context
import android.util.Log
import com.voicekeyboard.model.InferenceBackend
import com.voicekeyboard.model.VoiceModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.tensorflow.lite.Interpreter
import org.tensorflow.lite.gpu.CompatibilityList
import org.tensorflow.lite.gpu.GpuDelegate
import java.io.File
import java.nio.FloatBuffer
import kotlin.math.min

/**
 * Unified inference engine wrapping both TFLite and ONNX Runtime backends.
 * Handles Whisper-style encoder-decoder with log-mel spectrogram preprocessing.
 */
class InferenceEngine(private val context: Context) {

    private var tfliteInterpreter: Interpreter? = null
    private var onnxSession: ai.onnxruntime.OrtSession? = null
    private var onnxEnv: ai.onnxruntime.OrtEnvironment? = null
    private var gpuDelegate: GpuDelegate? = null
    private var currentModel: VoiceModel? = null

    private val preprocessor = AudioPreprocessor()

    suspend fun loadModel(model: VoiceModel, modelFile: File) = withContext(Dispatchers.IO) {
        unload()
        currentModel = model
        when (model.backend) {
            InferenceBackend.TFLITE -> loadTflite(modelFile)
            InferenceBackend.ONNX -> loadOnnx(modelFile)
        }
        Log.i(TAG, "Loaded model: ${model.name} via ${model.backend}")
    }

    private fun loadTflite(file: File) {
        val compatList = CompatibilityList()
        val options = Interpreter.Options().apply {
            if (compatList.isDelegateSupportedOnThisDevice) {
                gpuDelegate = GpuDelegate(compatList.bestOptionsForThisDevice)
                addDelegate(gpuDelegate)
            } else {
                setNumThreads(4)
            }
        }
        tfliteInterpreter = Interpreter(file, options)
    }

    private fun loadOnnx(file: File) {
        onnxEnv = ai.onnxruntime.OrtEnvironment.getEnvironment()
        val opts = ai.onnxruntime.OrtSession.SessionOptions().apply {
            setIntraOpNumThreads(4)
            setOptimizationLevel(ai.onnxruntime.OrtSession.SessionOptions.OptLevel.ALL_OPT)
        }
        onnxSession = onnxEnv!!.createSession(file.absolutePath, opts)
    }

    suspend fun transcribe(pcmFloats: FloatArray): String = withContext(Dispatchers.Default) {
        val model = currentModel ?: return@withContext ""
        if (pcmFloats.size < 100) return@withContext ""

        val melFrames = preprocessor.computeLogMelSpectrogram(pcmFloats, model.sampleRate)
        return@withContext when (model.backend) {
            InferenceBackend.TFLITE -> transcribeTflite(melFrames)
            InferenceBackend.ONNX -> transcribeOnnx(melFrames)
        }
    }

    private fun transcribeTflite(melFrames: Array<FloatArray>): String {
        val interp = tfliteInterpreter ?: return ""
        // Whisper TFLite: input [1, 80, 3000] mel spectrogram; output [1, maxTokens] token IDs
        val nMels = 80
        val nFrames = 3000
        val inputBuf = FloatBuffer.allocate(1 * nMels * nFrames)
        val paddedMel = padOrTruncate(melFrames, nFrames)
        for (mel in paddedMel) for (v in mel) inputBuf.put(v)
        inputBuf.rewind()

        val outputTokens = Array(1) { IntArray(448) }  // Whisper max decode length
        interp.run(inputBuf, outputTokens)

        return decodeTokenIds(outputTokens[0])
    }

    private fun transcribeOnnx(melFrames: Array<FloatArray>): String {
        val session = onnxSession ?: return ""
        val env = onnxEnv ?: return ""

        val nMels = 80
        val nFrames = 3000
        val paddedMel = padOrTruncate(melFrames, nFrames)
        val flat = FloatArray(nMels * nFrames)
        var idx = 0
        for (mel in paddedMel) for (v in mel) flat[idx++] = v

        val shape = longArrayOf(1, nMels.toLong(), nFrames.toLong())
        val tensor = ai.onnxruntime.OnnxTensor.createTensor(env, FloatBuffer.wrap(flat), shape)
        val result = session.run(mapOf("mel_input" to tensor))
        val logits = result[0].value as Array<*>
        tensor.close()
        result.close()

        val tokenIds = decodeGreedy(logits)
        return decodeTokenIds(tokenIds)
    }

    // ── helpers ────────────────────────────────────────────────────────────────

    private fun padOrTruncate(mel: Array<FloatArray>, targetLen: Int): Array<FloatArray> {
        val nMels = mel.size
        return Array(nMels) { m ->
            FloatArray(targetLen).also { row ->
                val src = mel[m]
                val copy = min(src.size, targetLen)
                System.arraycopy(src, 0, row, 0, copy)
            }
        }
    }

    /** Greedy argmax decode of logit array from ONNX output */
    private fun decodeGreedy(logits: Array<*>): IntArray {
        @Suppress("UNCHECKED_CAST")
        val seq = logits as? Array<Array<FloatArray>> ?: return IntArray(0)
        return IntArray(seq[0].size) { t ->
            val frame = seq[0][t]
            var best = 0
            for (k in frame.indices) if (frame[k] > frame[best]) best = k
            best
        }
    }

    /**
     * Stub tokenizer — in a shipping app this would use the Whisper BPE vocab.
     * We return a placeholder string to demonstrate the pipeline.
     */
    private fun decodeTokenIds(tokens: IntArray): String {
        val eosId = 50257
        val filtered = tokens.takeWhile { it != eosId && it > 0 }
        return if (filtered.isEmpty()) "" else "[voice: ${filtered.size} tokens recognised]"
    }

    fun unload() {
        tfliteInterpreter?.close()
        tfliteInterpreter = null
        gpuDelegate?.close()
        gpuDelegate = null
        onnxSession?.close()
        onnxSession = null
        onnxEnv?.close()
        onnxEnv = null
        currentModel = null
    }

    companion object {
        private const val TAG = "InferenceEngine"
    }
}
