package com.voicekeyboard.inference

import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.isActive
import kotlinx.coroutines.withContext
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.sqrt

class AudioRecorder(private val sampleRate: Int = 16000) {

    private var audioRecord: AudioRecord? = null
    private val bufferSize = AudioRecord.getMinBufferSize(
        sampleRate,
        AudioFormat.CHANNEL_IN_MONO,
        AudioFormat.ENCODING_PCM_16BIT
    ).coerceAtLeast(sampleRate * 2)   // at least 1 s worth

    private val _pcmBuffer = mutableListOf<Short>()

    val isRecording: Boolean get() = audioRecord?.recordingState == AudioRecord.RECORDSTATE_RECORDING

    fun startRecording() {
        if (isRecording) return
        _pcmBuffer.clear()
        audioRecord = AudioRecord(
            MediaRecorder.AudioSource.VOICE_RECOGNITION,
            sampleRate,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
            bufferSize
        ).also { it.startRecording() }
    }

    suspend fun readChunksUntilStopped(
        onVoiceActivity: (Boolean) -> Unit,
        onChunk: (FloatArray) -> Unit
    ) = withContext(Dispatchers.IO) {
        val chunk = ShortArray(bufferSize / 2)
        var silenceFrames = 0
        val silenceThreshold = 300      // RMS below this → silence
        val maxSilenceFrames = 30       // ~30 * bufferSize/sampleRate ≈ 1.5 s

        while (isActive && isRecording) {
            val read = audioRecord?.read(chunk, 0, chunk.size) ?: break
            if (read <= 0) continue

            val rms = computeRms(chunk, read)
            val voiceActive = rms > silenceThreshold
            onVoiceActivity(voiceActive)

            if (voiceActive) {
                silenceFrames = 0
                _pcmBuffer.addAll(chunk.take(read))
                val floats = shortsToFloats(chunk, read)
                onChunk(floats)
            } else {
                silenceFrames++
                if (silenceFrames > maxSilenceFrames && _pcmBuffer.isNotEmpty()) {
                    // Natural end of utterance
                    break
                }
            }
        }
    }

    fun stopRecording() {
        audioRecord?.stop()
        audioRecord?.release()
        audioRecord = null
    }

    fun getPcmData(): FloatArray = shortsToFloatsFromList(_pcmBuffer)

    private fun computeRms(samples: ShortArray, count: Int): Double {
        var sum = 0.0
        repeat(count) { sum += samples[it] * samples[it].toDouble() }
        return sqrt(sum / count)
    }

    private fun shortsToFloats(shorts: ShortArray, count: Int): FloatArray {
        val floats = FloatArray(count)
        repeat(count) { floats[it] = shorts[it] / 32768f }
        return floats
    }

    private fun shortsToFloatsFromList(shorts: List<Short>): FloatArray {
        val floats = FloatArray(shorts.size)
        shorts.forEachIndexed { i, s -> floats[i] = s / 32768f }
        return floats
    }

    fun floatArrayToByteBuffer(floats: FloatArray): ByteBuffer {
        val buf = ByteBuffer.allocateDirect(floats.size * 4).order(ByteOrder.nativeOrder())
        floats.forEach { buf.putFloat(it) }
        buf.rewind()
        return buf
    }
}
