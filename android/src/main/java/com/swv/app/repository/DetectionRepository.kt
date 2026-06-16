package com.swv.app.repository

import okhttp3.MultipartBody
import com.swv.app.api.DetectionApi
import com.swv.app.models.DetectionResponse
import timber.log.Timber

class DetectionRepository(private val api: DetectionApi, private val apiKey: String) {
    
    suspend fun detectObjects(
        file: MultipartBody.Part,
        confidence: Float = 0.5f
    ): Result<DetectionResponse> = try {
        val response = api.detectObjects(file, confidence, apiKey)
        Result.success(response)
    } catch (e: Exception) {
        Timber.e(e, "Detection failed")
        Result.failure(e)
    }
    
    suspend fun checkHealth(): Result<Boolean> = try {
        val response = api.checkHealth()
        Result.success(response.status == "healthy")
    } catch (e: Exception) {
        Timber.e(e, "Health check failed")
        Result.failure(e)
    }
    
    suspend fun getInfo(): Result<Map<String, Any>> = try {
        val response = api.getInfo()
        Result.success(response)
    } catch (e: Exception) {
        Timber.e(e, "Failed to get info")
        Result.failure(e)
    }
}
