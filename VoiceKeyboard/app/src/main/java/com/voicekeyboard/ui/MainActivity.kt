package com.voicekeyboard.ui

import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import android.view.inputmethod.InputMethodManager
import androidx.appcompat.app.AppCompatActivity
import com.voicekeyboard.databinding.ActivityMainBinding
import com.voicekeyboard.model.ModelGallery

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var gallery: ModelGallery

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)

        gallery = ModelGallery(this)
        updateStatus()

        binding.btnEnableIme.setOnClickListener {
            startActivity(Intent(Settings.ACTION_INPUT_METHOD_SETTINGS))
        }

        binding.btnSelectIme.setOnClickListener {
            val imm = getSystemService(INPUT_METHOD_SERVICE) as InputMethodManager
            imm.showInputMethodPicker()
        }

        binding.btnOpenGallery.setOnClickListener {
            startActivityForResult(
                Intent(this, ModelGalleryActivity::class.java), REQUEST_GALLERY
            )
        }

        binding.btnTestKeyboard.setOnClickListener {
            binding.etTestInput.requestFocus()
            val imm = getSystemService(INPUT_METHOD_SERVICE) as InputMethodManager
            imm.showSoftInput(binding.etTestInput, InputMethodManager.SHOW_IMPLICIT)
        }
    }

    override fun onResume() {
        super.onResume()
        updateStatus()
    }

    @Deprecated("Deprecated in Java")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == REQUEST_GALLERY) updateStatus()
    }

    private fun updateStatus() {
        val active = gallery.activeModel
        val downloaded = gallery.isModelDownloaded(active)
        binding.tvCurrentModel.text = "Active model: ${active.name}"
        binding.tvModelStatus.text = if (downloaded) "Ready for inference" else "Not installed — open Model Gallery"
        binding.tvModelDetails.text = "${active.displaySize}  •  ${active.backend}  •  ${active.qualityLabel} quality"
    }

    companion object {
        private const val REQUEST_GALLERY = 1001
    }
}
