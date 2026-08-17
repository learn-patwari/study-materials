package com.voicekeyboard.ui

import android.os.Bundle
import android.widget.SeekBar
import androidx.appcompat.app.AppCompatActivity
import com.voicekeyboard.databinding.ActivitySettingsBinding

class SettingsActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySettingsBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySettingsBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        val prefs = getSharedPreferences("voice_keyboard_settings", MODE_PRIVATE)

        // VAD threshold
        val vadThresholdPref = prefs.getInt("vad_threshold", 50)
        binding.seekVadThreshold.progress = vadThresholdPref
        binding.tvVadValue.text = "%.2f".format(vadThresholdPref / 100f)
        binding.seekVadThreshold.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(sb: SeekBar?, progress: Int, fromUser: Boolean) {
                binding.tvVadValue.text = "%.2f".format(progress / 100f)
                prefs.edit().putInt("vad_threshold", progress).apply()
            }
            override fun onStartTrackingTouch(sb: SeekBar?) {}
            override fun onStopTrackingTouch(sb: SeekBar?) {}
        })

        // Haptic feedback
        val hapticPref = prefs.getBoolean("haptic_feedback", true)
        binding.switchHaptic.isChecked = hapticPref
        binding.switchHaptic.setOnCheckedChangeListener { _, checked ->
            prefs.edit().putBoolean("haptic_feedback", checked).apply()
        }

        // GPU acceleration
        val gpuPref = prefs.getBoolean("gpu_acceleration", true)
        binding.switchGpu.isChecked = gpuPref
        binding.switchGpu.setOnCheckedChangeListener { _, checked ->
            prefs.edit().putBoolean("gpu_acceleration", checked).apply()
        }

        // Auto-punctuate
        val autoPunctPref = prefs.getBoolean("auto_punctuate", false)
        binding.switchAutoPunct.isChecked = autoPunctPref
        binding.switchAutoPunct.setOnCheckedChangeListener { _, checked ->
            prefs.edit().putBoolean("auto_punctuate", checked).apply()
        }
    }
}
