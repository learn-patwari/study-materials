package com.voicekeyboard.inference

import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.ln
import kotlin.math.log10
import kotlin.math.max
import kotlin.math.pow
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Computes a log-Mel spectrogram matching the Whisper model's expected input:
 *   80 Mel bins, 25 ms windows at 10 ms hop, 16 kHz input.
 */
class AudioPreprocessor {

    private val nMels = 80
    private val nFft = 400           // 25 ms window at 16 kHz
    private val hopLength = 160      // 10 ms hop
    private val fMin = 0.0
    private val fMax = 8000.0

    private val hanningWindow = FloatArray(nFft) { n ->
        (0.5 * (1 - cos(2 * PI * n / nFft))).toFloat()
    }

    private val melFilters: Array<FloatArray> by lazy { buildMelFilters(16000) }

    fun computeLogMelSpectrogram(audio: FloatArray, sampleRate: Int): Array<FloatArray> {
        val frames = stft(audio)                    // [nFft/2+1, nFrames]
        val power = powerSpectrum(frames)           // magnitude^2
        val melSpec = applyMelFilters(power)        // [nMels, nFrames]
        return logMel(melSpec)
    }

    private fun stft(audio: FloatArray): Array<FloatArray> {
        val padded = FloatArray(audio.size + nFft) // zero-pad start
        System.arraycopy(audio, 0, padded, nFft / 2, audio.size)

        val nFrames = (padded.size - nFft) / hopLength + 1
        val nBins = nFft / 2 + 1
        val magnitudes = Array(nBins) { FloatArray(nFrames) }

        val real = DoubleArray(nFft)
        val imag = DoubleArray(nFft)

        for (t in 0 until nFrames) {
            val offset = t * hopLength
            for (n in 0 until nFft) {
                val sample = if (offset + n < padded.size) padded[offset + n] else 0f
                real[n] = sample * hanningWindow[n]
                imag[n] = 0.0
            }
            fft(real, imag)
            for (k in 0 until nBins) {
                magnitudes[k][t] = sqrt(real[k] * real[k] + imag[k] * imag[k]).toFloat()
            }
        }
        return magnitudes
    }

    private fun powerSpectrum(magnitudes: Array<FloatArray>): Array<FloatArray> =
        Array(magnitudes.size) { k ->
            FloatArray(magnitudes[k].size) { t ->
                magnitudes[k][t] * magnitudes[k][t]
            }
        }

    private fun applyMelFilters(power: Array<FloatArray>): Array<FloatArray> {
        val nFrames = power[0].size
        return Array(nMels) { m ->
            FloatArray(nFrames) { t ->
                var sum = 0f
                for (k in power.indices) sum += melFilters[m][k] * power[k][t]
                sum
            }
        }
    }

    private fun logMel(mel: Array<FloatArray>): Array<FloatArray> {
        var maxVal = 1e-10f
        for (row in mel) for (v in row) if (v > maxVal) maxVal = v
        val floor = maxVal * 1e-4f
        return Array(mel.size) { m ->
            FloatArray(mel[m].size) { t ->
                val v = max(mel[m][t], floor)
                ((log10(v.toDouble()) + 4.0) / 4.0).toFloat().coerceIn(-1f, 1f)
            }
        }
    }

    private fun buildMelFilters(sampleRate: Int): Array<FloatArray> {
        val nBins = nFft / 2 + 1
        val fLow = hzToMel(fMin)
        val fHigh = hzToMel(fMax)
        val melPoints = DoubleArray(nMels + 2) { i -> fLow + i * (fHigh - fLow) / (nMels + 1) }
        val hzPoints = DoubleArray(melPoints.size) { melToHz(melPoints[it]) }
        val binPoints = IntArray(hzPoints.size) { i ->
            ((hzPoints[i] / sampleRate) * nFft).toInt().coerceIn(0, nBins - 1)
        }
        return Array(nMels) { m ->
            FloatArray(nBins) { k ->
                when {
                    k < binPoints[m] || k > binPoints[m + 2] -> 0f
                    k <= binPoints[m + 1] ->
                        (k - binPoints[m]).toFloat() / (binPoints[m + 1] - binPoints[m]).coerceAtLeast(1)
                    else ->
                        (binPoints[m + 2] - k).toFloat() / (binPoints[m + 2] - binPoints[m + 1]).coerceAtLeast(1)
                }
            }
        }
    }

    // Cooley-Tukey FFT in-place
    private fun fft(re: DoubleArray, im: DoubleArray) {
        val n = re.size
        var j = 0
        for (i in 1 until n) {
            var bit = n shr 1
            while (j and bit != 0) { j = j xor bit; bit = bit shr 1 }
            j = j xor bit
            if (i < j) { swap(re, i, j); swap(im, i, j) }
        }
        var len = 2
        while (len <= n) {
            val ang = -2 * PI / len
            val wRe = cos(ang); val wIm = sin(ang)
            var i = 0
            while (i < n) {
                var curRe = 1.0; var curIm = 0.0
                for (jj in 0 until len / 2) {
                    val uRe = re[i + jj]; val uIm = im[i + jj]
                    val vRe = re[i + jj + len / 2] * curRe - im[i + jj + len / 2] * curIm
                    val vIm = re[i + jj + len / 2] * curIm + im[i + jj + len / 2] * curRe
                    re[i + jj] = uRe + vRe; im[i + jj] = uIm + vIm
                    re[i + jj + len / 2] = uRe - vRe; im[i + jj + len / 2] = uIm - vIm
                    val tmp = curRe * wRe - curIm * wIm
                    curIm = curRe * wIm + curIm * wRe; curRe = tmp
                }
                i += len
            }
            len = len shl 1
        }
    }

    private fun swap(a: DoubleArray, i: Int, j: Int) { val t = a[i]; a[i] = a[j]; a[j] = t }
    private fun hzToMel(hz: Double) = 2595 * log10(1 + hz / 700)
    private fun melToHz(mel: Double) = 700 * (10.0.pow(mel / 2595) - 1)
}
