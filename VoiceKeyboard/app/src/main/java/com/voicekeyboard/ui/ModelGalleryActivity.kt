package com.voicekeyboard.ui

import android.app.Activity
import android.os.Bundle
import android.view.LayoutInflater
import android.view.ViewGroup
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.voicekeyboard.R
import com.voicekeyboard.databinding.ActivityModelGalleryBinding
import com.voicekeyboard.databinding.ItemModelCardBinding
import com.voicekeyboard.model.ModelGallery
import com.voicekeyboard.model.VoiceModel
import java.io.File
import java.io.FileOutputStream

class ModelGalleryActivity : AppCompatActivity() {

    private lateinit var binding: ActivityModelGalleryBinding
    private lateinit var gallery: ModelGallery
    private lateinit var adapter: ModelAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityModelGalleryBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        gallery = ModelGallery(this)
        adapter = ModelAdapter(gallery.enrichedCatalog(), ::onModelAction)

        binding.recyclerView.apply {
            layoutManager = LinearLayoutManager(this@ModelGalleryActivity)
            adapter = this@ModelGalleryActivity.adapter
        }
    }

    private fun onModelAction(model: VoiceModel) {
        if (!gallery.isModelDownloaded(model)) {
            copyBundledModelIfAvailable(model)
        } else {
            gallery.setActiveModel(model)
            adapter.updateList(gallery.enrichedCatalog())
            Toast.makeText(this, "${model.name} set as active model", Toast.LENGTH_SHORT).show()
            setResult(Activity.RESULT_OK)
        }
    }

    /**
     * In production: download from a model hub.  For bundled demo assets in /assets/models/
     * we copy straight to the internal files dir.
     */
    private fun copyBundledModelIfAvailable(model: VoiceModel) {
        val assetPath = "models/${model.fileName}"
        val dest = gallery.modelFile(model)
        try {
            assets.open(assetPath).use { input ->
                FileOutputStream(dest).use { out ->
                    input.copyTo(out)
                }
            }
            gallery.saveDownloadedState(model, true)
            adapter.updateList(gallery.enrichedCatalog())
            Toast.makeText(this, "${model.name} ready", Toast.LENGTH_SHORT).show()
        } catch (e: Exception) {
            Toast.makeText(
                this,
                "Model not bundled. Place ${model.fileName} in assets/models/ and rebuild.",
                Toast.LENGTH_LONG
            ).show()
        }
    }

    // ── Adapter ────────────────────────────────────────────────────────────────

    inner class ModelAdapter(
        private var models: List<VoiceModel>,
        private val onAction: (VoiceModel) -> Unit
    ) : RecyclerView.Adapter<ModelAdapter.VH>() {

        inner class VH(val binding: ItemModelCardBinding) : RecyclerView.ViewHolder(binding.root)

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
            VH(ItemModelCardBinding.inflate(LayoutInflater.from(parent.context), parent, false))

        override fun getItemCount() = models.size

        override fun onBindViewHolder(holder: VH, position: Int) {
            val m = models[position]
            with(holder.binding) {
                tvName.text = m.name
                tvDescription.text = m.description
                tvSize.text = m.displaySize
                tvBackend.text = m.backend.name
                tvQuality.text = "Quality: ${m.qualityLabel}  •  Speed: ${m.speedLabel}"
                chipLanguage.text = m.language.uppercase()

                val isDownloaded = gallery.isModelDownloaded(m)
                btnAction.text = when {
                    m.isActive -> "Active"
                    isDownloaded -> "Set Active"
                    else -> "Install"
                }
                btnAction.isEnabled = !m.isActive
                activeIndicator.visibility = if (m.isActive) android.view.View.VISIBLE else android.view.View.GONE

                btnAction.setOnClickListener { onAction(m) }
            }
        }

        fun updateList(newList: List<VoiceModel>) {
            models = newList
            notifyDataSetChanged()
        }
    }
}
