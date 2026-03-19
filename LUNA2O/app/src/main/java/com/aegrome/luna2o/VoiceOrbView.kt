package com.aegrome.luna2o


import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.util.AttributeSet
import android.view.View
import kotlin.math.sin

class VoiceOrbView(context: Context, attrs: AttributeSet?) : View(context, attrs) {

    private val corePaint = Paint()
    private val ringPaint = Paint()

    private var radius = 90f
    private var time = 0f
    var voiceLevel = 0f

    init {
        corePaint.color = Color.CYAN
        corePaint.style = Paint.Style.FILL
        corePaint.isAntiAlias = true
        corePaint.setShadowLayer(40f, 0f, 0f, Color.CYAN)

        ringPaint.color = Color.CYAN
        ringPaint.style = Paint.Style.STROKE
        ringPaint.strokeWidth = 6f
        ringPaint.isAntiAlias = true

        setLayerType(LAYER_TYPE_SOFTWARE, null) // enables glow
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)

        val cx = width / 2f
        val cy = height / 2f
        val animatedRadius = radius + (voiceLevel * 30) + 15 * sin(time)

        // core orb
        canvas.drawCircle(cx, cy, animatedRadius.toFloat(), corePaint)

        // outer animated ring
        val ringRadius = animatedRadius + 40 + 10 * sin(time * 1.5)
        canvas.drawCircle(cx, cy, ringRadius.toFloat(), ringPaint)

        // second outer ring
        val ringRadius2 = animatedRadius + 70 + 10 * sin(time * 1.2)
        canvas.drawCircle(cx, cy, ringRadius2.toFloat(), ringPaint)

        time += 0.08f
        invalidate()
    }

    fun updateVoiceLevel(level: Float) {
        voiceLevel = level
    }

}