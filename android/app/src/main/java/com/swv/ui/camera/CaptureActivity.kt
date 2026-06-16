package com.swv.ui.camera

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.MediaStore
import android.widget.ImageView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.Toolbar
import com.google.android.material.button.MaterialButton
import com.swv.R
import com.swv.service.AnalysisService
import com.swv.service.LocationService
import com.swv.utils.Constants
import com.swv.utils.PermissionUtils
import timber.log.Timber
import java.io.File
import java.io.FileOutputStream

class CaptureActivity : AppCompatActivity() {

    private lateinit var imagePreview: ImageView
    private var capturedImageUri: Uri? = null
    private var capturedImagePath: String? = null
    private lateinit var locationService: LocationService

    private val cameraLauncher = registerForActivityResult(
        ActivityResultContracts.TakePicture()
    ) { success ->
        if (success) {
            capturedImageUri?.let { loadAndAnalyze(it) }
        } else {
            Toast.makeText(this, "Capture cancelled", Toast.LENGTH_SHORT).show()
        }
    }

    private val galleryLauncher = registerForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri ->
        uri?.let { loadAndAnalyze(it) }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_capture)

        locationService = LocationService(this)
        imagePreview = findViewById(R.id.image_preview)

        val toolbar: Toolbar = findViewById(R.id.toolbar)
        setSupportActionBar(toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        supportActionBar?.title = "Capture Image"

        findViewById<MaterialButton>(R.id.btn_camera).setOnClickListener {
            if (PermissionUtils.hasCameraPermission(this)) {
                openCamera()
            } else {
                PermissionUtils.requestCameraPermission(this)
            }
        }

        findViewById<MaterialButton>(R.id.btn_gallery).setOnClickListener {
            if (PermissionUtils.hasStoragePermission(this)) {
                openGallery()
            } else {
                PermissionUtils.requestStoragePermission(this)
            }
        }
    }

    private fun openCamera() {
        val photoFile = createTempImageFile()
        val uri = Uri.fromFile(photoFile)
        capturedImageUri = uri
        capturedImagePath = photoFile.absolutePath
        val intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE).apply {
            putExtra(MediaStore.EXTRA_OUTPUT, uri)
        }
        cameraLauncher.launch(uri)
    }

    private fun openGallery() {
        galleryLauncher.launch("image/*")
    }

    private fun loadAndAnalyze(uri: Uri) {
        imagePreview.setImageURI(uri)
        copyUriToFile(uri) { filePath ->
            capturedImagePath = filePath
            locationService.getCurrentLocation { geoLocation ->
                val lat = geoLocation?.latitude ?: 0.0
                val lon = geoLocation?.longitude ?: 0.0

                val intent = Intent(this, AnalysisService::class.java).apply {
                    putExtra(AnalysisService.EXTRA_IMAGE_PATH, filePath)
                    putExtra(AnalysisService.EXTRA_LATITUDE, lat)
                    putExtra(AnalysisService.EXTRA_LONGITUDE, lon)
                    putExtra(AnalysisService.EXTRA_CONFIDENCE, Constants.DEFAULT_CONFIDENCE)
                }
                startService(intent)
                Toast.makeText(this, "Analysis started...", Toast.LENGTH_SHORT).show()
                finish()
            }
        }
    }

    private fun createTempImageFile(): File {
        val dir = File(cacheDir, "captures")
        dir.mkdirs()
        return File(dir, "SWV_${System.currentTimeMillis()}.jpg")
    }

    private fun copyUriToFile(uri: Uri, callback: (String) -> Unit) {
        try {
            val inputStream = contentResolver.openInputStream(uri)
            val file = createTempImageFile()
            inputStream?.use { input ->
                FileOutputStream(file).use { output ->
                    input.copyTo(output)
                }
            }
            callback(file.absolutePath)
        } catch (e: Exception) {
            Timber.e(e, "Failed to copy image")
            Toast.makeText(this, "Failed to process image", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onSupportNavigateUp(): Boolean {
        onBackPressed()
        return true
    }
}
