package com.swv.app.api

import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.GET
import retrofit2.http.Query
import retrofit2.http.Header
import okhttp3.MultipartBody
import com.swv.app.models.DetectionResponse
import com.swv.app.models.HealthResponse

interface DetectionApi {
    
    @GET("api/v1/health")
    suspend fun checkHealth(): HealthResponse
    
    @GET("api/v1/info")
    suspend fun getInfo(): Map<String, Any>
    
    @Multipart
    @POST("api/v1/detect")
    suspend fun detectObjects(
        @Part file: MultipartBody.Part,
        @Query("confidence") confidence: Float = 0.5f,
        @Header("X-API-Key") apiKey: String
    ): DetectionResponse
}
