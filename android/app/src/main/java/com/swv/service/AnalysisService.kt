package com.swv.service

import android.app.Service
import android.content.Intent
import android.os.IBinder
import com.swv.api.ApiClient
import com.swv.api.models.EnvironmentalReport
import com.swv.utils.Constants
import kotlinx.coroutines.*
import timber.log.Timber
import java.io.File

class AnalysisService : Service() {

    private val serviceScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var currentJob: Job? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        intent?.let {
            val imagePath = it.getStringExtra(EXTRA_IMAGE_PATH)
            val latitude = it.getDoubleExtra(EXTRA_LATITUDE, 0.0)
            val longitude = it.getDoubleExtra(EXTRA_LONGITUDE, 0.0)
            val confidence = it.getFloatExtra(EXTRA_CONFIDENCE, Constants.DEFAULT_CONFIDENCE)

            if (imagePath != null) {
                startAnalysis(imagePath, latitude, longitude, confidence)
            }
        }
        return START_REDELIVER_INTENT
    }

    private fun startAnalysis(imagePath: String, latitude: Double, longitude: Double, confidence: Float) {
        currentJob = serviceScope.launch {
            try {
                val file = File(imagePath)
                if (!file.exists()) {
                    sendBroadcast(Intent(ACTION_ANALYSIS_ERROR).apply {
                        putExtra(EXTRA_ERROR, "Image file not found")
                    })
                    return@launch
                }

                val requestBody = okhttp3.MultipartBody.Part.createFormData(
                    "file", file.name,
                    okhttp3.RequestBody.create(okhttp3.MediaType.parse("image/*"), file)
                )

                val api = ApiClient.getApiService()
                val report = api.analyzeSmoke(
                    file = requestBody,
                    latitude = latitude,
                    longitude = longitude,
                    confidence = confidence,
                    apiKey = ApiClient.getApiKey()
                )

                sendBroadcast(Intent(ACTION_ANALYSIS_COMPLETE).apply {
                    putExtra(EXTRA_REPORT_ID, report.reportId)
                })

                Timber.i("Analysis complete: ${report.reportId}")

            } catch (e: Exception) {
                Timber.e(e, "Analysis failed")
                sendBroadcast(Intent(ACTION_ANALYSIS_ERROR).apply {
                    putExtra(EXTRA_ERROR, e.message ?: "Unknown error")
                })
            } finally {
                stopSelf()
            }
        }
    }

    override fun onDestroy() {
        currentJob?.cancel()
        serviceScope.cancel()
        super.onDestroy()
    }

    companion object {
        const val ACTION_ANALYSIS_COMPLETE = "com.swv.action.ANALYSIS_COMPLETE"
        const val ACTION_ANALYSIS_ERROR = "com.swv.action.ANALYSIS_ERROR"

        const val EXTRA_IMAGE_PATH = "image_path"
        const val EXTRA_LATITUDE = "latitude"
        const val EXTRA_LONGITUDE = "longitude"
        const val EXTRA_CONFIDENCE = "confidence"
        const val EXTRA_REPORT_ID = "report_id"
        const val EXTRA_ERROR = "error"
    }
}
