package com.voicekeyboard

import android.content.Intent
import android.inputmethodservice.InputMethodService
import android.os.Handler
import android.os.Looper
import android.view.View
import android.view.inputmethod.EditorInfo
import android.widget.Toast
import com.voicekeyboard.inference.AudioRecorder
import com.voicekeyboard.inference.InferenceEngine
import com.voicekeyboard.inference.VadEngine
import com.voicekeyboard.model.ModelGallery
import com.voicekeyboard.ui.KeyboardView
import com.voicekeyboard.ui.ModelGalleryActivity
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

class VoiceInputMethodService : InputMethodService(), KeyboardView.KeyboardCallback {

    private lateinit var keyboardView: KeyboardView
    private lateinit var audioRecorder: AudioRecorder
    private lateinit var inferenceEngine: InferenceEngine
    private lateinit var vadEngine: VadEngine
    private lateinit var modelGallery: ModelGallery

    private val serviceScope = CoroutineScope(Dispatchers.Main + Job())
    private val mainHandler = Handler(Looper.getMainLooper())

    private var recordingJob: Job? = null
    private var isModelLoaded = false

    // ── lifecycle ──────────────────────────────────────────────────────────────

    override fun onCreate() {
        super.onCreate()
        modelGallery = ModelGallery(this)
        audioRecorder = AudioRecorder()
        inferenceEngine = InferenceEngine(this)
        vadEngine = VadEngine(this)
        loadActiveModel()
    }

    override fun onCreateInputView(): View {
        keyboardView = KeyboardView(this, this)
        return keyboardView
    }

    override fun onStartInputView(info: EditorInfo?, restarting: Boolean) {
        super.onStartInputView(info, restarting)
        keyboardView.setInputType(info?.inputType ?: 0)
        keyboardView.updateModelName(modelGallery.activeModel.name)
    }

    override fun onDestroy() {
        serviceScope.cancel()
        audioRecorder.stopRecording()
        inferenceEngine.unload()
        vadEngine.unload()
        super.onDestroy()
    }

    // ── KeyboardCallback ───────────────────────────────────────────────────────

    override fun onKeyChar(char: Char) {
        currentInputConnection?.commitText(char.toString(), 1)
    }

    override fun onBackspace() {
        currentInputConnection?.deleteSurroundingText(1, 0)
    }

    override fun onEnter() {
        sendDefaultEditorAction(true)
    }

    override fun onSpace() {
        currentInputConnection?.commitText(" ", 1)
    }

    override fun onVoiceButtonPressed() {
        if (!isModelLoaded) {
            showToast("Model not ready — open app to download a model")
            return
        }
        if (audioRecorder.isRecording) {
            stopVoiceCapture()
        } else {
            startVoiceCapture()
        }
    }

    override fun onModelGalleryRequested() {
        val intent = Intent(this, ModelGalleryActivity::class.java).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        startActivity(intent)
    }

    override fun onDeleteWord() {
        val ic = currentInputConnection ?: return
        val before = ic.getTextBeforeCursor(100, 0) ?: return
        val trimmed = before.trimEnd()
        val wordStart = trimmed.lastIndexOf(' ')
        val deleteCount = if (wordStart == -1) trimmed.length else trimmed.length - wordStart
        ic.deleteSurroundingText(deleteCount + (before.length - trimmed.length), 0)
    }

    // ── voice capture pipeline ─────────────────────────────────────────────────

    private fun startVoiceCapture() {
        audioRecorder.startRecording()
        keyboardView.setRecordingState(true)
        vadEngine.resetState()

        recordingJob = serviceScope.launch(Dispatchers.IO) {
            val accumulatedPcm = mutableListOf<Float>()
            var hasVoice = false

            audioRecorder.readChunksUntilStopped(
                onVoiceActivity = { active ->
                    mainHandler.post { keyboardView.setVoiceActivity(active) }
                    if (active) hasVoice = true
                },
                onChunk = { chunk ->
                    if (vadEngine.isVoice(chunk)) {
                        accumulatedPcm.addAll(chunk.toList())
                    }
                }
            )

            if (hasVoice && accumulatedPcm.isNotEmpty()) {
                mainHandler.post { keyboardView.setInferenceState(true) }
                val transcript = inferenceEngine.transcribe(accumulatedPcm.toFloatArray())
                mainHandler.post {
                    keyboardView.setInferenceState(false)
                    keyboardView.setRecordingState(false)
                    if (transcript.isNotBlank()) {
                        commitTranscript(transcript)
                    }
                }
            } else {
                mainHandler.post {
                    keyboardView.setRecordingState(false)
                }
            }
        }
    }

    private fun stopVoiceCapture() {
        audioRecorder.stopRecording()
        recordingJob?.cancel()
        keyboardView.setRecordingState(false)
        keyboardView.setVoiceActivity(false)
    }

    private fun commitTranscript(text: String) {
        val ic = currentInputConnection ?: return
        // Insert with smart capitalisation / space handling
        val before = ic.getTextBeforeCursor(1, 0)?.toString() ?: ""
        val prefix = if (before.isEmpty() || before == " ") "" else " "
        ic.commitText("$prefix$text", 1)
    }

    // ── model loading ──────────────────────────────────────────────────────────

    private fun loadActiveModel() {
        val model = modelGallery.activeModel
        val file = modelGallery.modelFile(model)
        if (!file.exists()) {
            isModelLoaded = false
            return
        }
        serviceScope.launch(Dispatchers.IO) {
            try {
                inferenceEngine.loadModel(model, file)
                val vadFile = modelGallery.modelFile(
                    modelGallery.catalog.first { it.id == "silero_vad_v4_onnx" }
                )
                vadEngine.load(vadFile)
                isModelLoaded = true
            } catch (e: Exception) {
                isModelLoaded = false
            }
        }
    }

    fun reloadModel() {
        isModelLoaded = false
        loadActiveModel()
    }

    private fun showToast(msg: String) =
        Toast.makeText(applicationContext, msg, Toast.LENGTH_SHORT).show()
}
