package com.voicekeyboard.ui

import android.animation.ValueAnimator
import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.util.AttributeSet
import android.view.View
import android.view.animation.LinearInterpolator

/** Animated concentric rings shown while recording is active. */
class VoiceRippleView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null
) : View(context, attrs) {

    private val basePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#4CAF50")
        style = Paint.Style.FILL
    }
    private val ripplePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#4CAF50")
        style = Paint.Style.STROKE
        strokeWidth = 3f
    }

    private var rippleRadius = 0f
    private var rippleAlpha = 0
    private var isActive = false
    private var pulseScale = 1f

    private val rippleAnimator = ValueAnimator.ofFloat(0f, 1f).apply {
        duration = 1200
        repeatCount = ValueAnimator.INFINITE
        interpolator = LinearInterpolator()
        addUpdateListener { anim ->
            val frac = anim.animatedValue as Float
            rippleRadius = (width / 2f) * (0.5f + frac * 0.5f)
            rippleAlpha = ((1f - frac) * 200).toInt()
            invalidate()
        }
    }

    private val pulseAnimator = ValueAnimator.ofFloat(1f, 1.2f, 1f).apply {
        duration = 300
        repeatCount = 0
        addUpdateListener { anim ->
            pulseScale = anim.animatedValue as Float
            invalidate()
        }
    }

    fun setActive(active: Boolean) {
        isActive = active
        if (active) {
            rippleAnimator.start()
        } else {
            rippleAnimator.cancel()
            rippleRadius = 0f
            rippleAlpha = 0
            invalidate()
        }
    }

    fun setPulse(voice: Boolean) {
        if (voice && isActive) pulseAnimator.start()
    }

    override fun onDraw(canvas: Canvas) {
        val cx = width / 2f
        val cy = height / 2f
        val baseR = (minOf(width, height) / 2f) * 0.4f * pulseScale

        if (isActive) {
            canvas.drawCircle(cx, cy, baseR, basePaint)
            ripplePaint.alpha = rippleAlpha
            canvas.drawCircle(cx, cy, rippleRadius, ripplePaint)
        }
    }
}
