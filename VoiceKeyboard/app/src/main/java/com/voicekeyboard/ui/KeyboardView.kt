package com.voicekeyboard.ui

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.inputmethodservice.InputMethodService
import android.os.Build
import android.util.DisplayMetrics
import android.util.TypedValue
import android.view.HapticFeedbackConstants
import android.view.LayoutInflater
import android.view.MotionEvent
import android.view.View
import android.view.ViewGroup
import android.widget.FrameLayout
import android.widget.ImageButton
import android.widget.TextView
import com.voicekeyboard.R

/**
 * Root keyboard view inflated by VoiceInputMethodService.
 * Hosts a standard QWERTY grid + a bottom action bar with voice controls.
 */
class KeyboardView(
    private val ims: InputMethodService,
    private val callback: KeyboardCallback
) : FrameLayout(ims) {

    interface KeyboardCallback {
        fun onKeyChar(char: Char)
        fun onBackspace()
        fun onEnter()
        fun onSpace()
        fun onDeleteWord()
        fun onVoiceButtonPressed()
        fun onModelGalleryRequested()
    }

    private val inflater = LayoutInflater.from(context)
    private lateinit var voiceButton: View
    private lateinit var modelLabel: TextView
    private lateinit var statusLabel: TextView
    private lateinit var rippleView: VoiceRippleView

    private var isShifted = false
    private var isSymbols = false

    private val rows = arrayOf(
        arrayOf("q", "w", "e", "r", "t", "y", "u", "i", "o", "p"),
        arrayOf("a", "s", "d", "f", "g", "h", "j", "k", "l"),
        arrayOf("⇧", "z", "x", "c", "v", "b", "n", "m", "⌫"),
        arrayOf("?123", ",", "SPACE", ".", "↵")
    )

    init {
        inflate()
    }

    private fun inflate() {
        val root = inflater.inflate(R.layout.keyboard_root, this, true)
        voiceButton = root.findViewById(R.id.btn_voice)
        modelLabel = root.findViewById(R.id.tv_model_name)
        statusLabel = root.findViewById(R.id.tv_status)
        rippleView = root.findViewById(R.id.voice_ripple)

        buildQwerty(root.findViewById(R.id.keyboard_grid))

        voiceButton.setOnClickListener {
            performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP)
            callback.onVoiceButtonPressed()
        }
        root.findViewById<View>(R.id.btn_model_gallery).setOnClickListener {
            callback.onModelGalleryRequested()
        }
    }

    private fun buildQwerty(container: ViewGroup) {
        container.removeAllViews()
        for (row in rows) {
            val rowView = inflater.inflate(R.layout.keyboard_row, container, false) as ViewGroup
            for (label in row) {
                val key = inflater.inflate(R.layout.keyboard_key, rowView, false)
                val tv = key.findViewById<TextView>(R.id.key_label)
                tv.text = if (isShifted && label.length == 1 && label[0].isLetter())
                    label.uppercase() else label
                when (label) {
                    "SPACE" -> key.layoutParams.width = dp(120)
                    "⇧", "⌫", "?123", "↵" -> key.layoutParams.width = dp(52)
                }
                key.setOnClickListener { handleKey(label) }
                key.setOnLongClickListener {
                    if (label == "⌫") { callback.onDeleteWord(); true } else false
                }
                rowView.addView(key)
            }
            container.addView(rowView)
        }
    }

    private fun handleKey(label: String) {
        performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP)
        when (label) {
            "⌫" -> callback.onBackspace()
            "↵" -> callback.onEnter()
            "SPACE" -> callback.onSpace()
            "⇧" -> toggleShift()
            "?123" -> { /* symbols layer — not implemented in this demo */ }
            else -> {
                val ch = if (isShifted) label[0].uppercaseChar() else label[0]
                callback.onKeyChar(ch)
                if (isShifted) { isShifted = false; rebuildKeys() }
            }
        }
    }

    private fun toggleShift() {
        isShifted = !isShifted
        rebuildKeys()
    }

    private fun rebuildKeys() {
        val container = findViewById<ViewGroup>(R.id.keyboard_grid)
        buildQwerty(container)
    }

    // ── public state setters ───────────────────────────────────────────────────

    fun setRecordingState(recording: Boolean) {
        val img = voiceButton as? ImageButton ?: return
        img.setImageResource(
            if (recording) R.drawable.ic_mic_active else R.drawable.ic_mic
        )
        rippleView.setActive(recording)
        statusLabel.text = if (recording) "Listening…" else ""
    }

    fun setVoiceActivity(active: Boolean) {
        rippleView.setPulse(active)
    }

    fun setInferenceState(inferring: Boolean) {
        statusLabel.text = if (inferring) "Transcribing…" else ""
    }

    fun updateModelName(name: String) {
        modelLabel.text = name
    }

    fun setInputType(inputType: Int) {
        // Could adapt keyboard layout for numeric fields etc.
    }

    private fun dp(v: Int) = TypedValue.applyDimension(
        TypedValue.COMPLEX_UNIT_DIP, v.toFloat(), resources.displayMetrics
    ).toInt()
}
