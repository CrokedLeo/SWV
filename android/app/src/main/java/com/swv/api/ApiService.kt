package com.swv.api

import com.swv.api.models.EnvironmentalReport
import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Response
import retrofit2.http.*

interface ApiService {

    @Multipart
    @POST("api/v1/analyze-smoke")
    suspend fun analyzeSmoke(
        @Part file: MultipartBody.Part,
        @Query("latitude") latitude: Double,
        @Query("longitude") longitude: Double,
        @Query("accuracy") accuracy: Double? = null,
        @Query("confidence") confidence: Float = 0.5f,
        @Query("include_weather") includeWeather: Boolean = true,
        @Header("X-API-Key") apiKey: String
    ): EnvironmentalReport

    @Multipart
    @POST("api/v1/analyze-smoke/summary")
    suspend fun getAnalysisSummary(
        @Part file: MultipartBody.Part,
        @Query("latitude") latitude: Double,
        @Query("longitude") longitude: Double,
        @Query("accuracy") accuracy: Double? = null,
        @Header("X-API-Key") apiKey: String
    ): Map<String, Any>

    @GET("api/v1/reports/history")
    suspend fun getReportsHistory(
        @Query("latitude") latitude: Double,
        @Query("longitude") longitude: Double,
        @Query("radius_km") radiusKm: Float = 10f,
        @Query("days") days: Int = 30,
        @Query("limit") limit: Int = 50,
        @Header("X-API-Key") apiKey: String
    ): Map<String, Any>

    @GET("api/v1/reports/{report_id}")
    suspend fun getReportById(
        @Path("report_id") reportId: String,
        @Header("X-API-Key") apiKey: String
    ): Map<String, Any>

    @GET("api/v1/reports/stats/location")
    suspend fun getLocationStats(
        @Query("latitude") latitude: Double,
        @Query("longitude") longitude: Double,
        @Query("days") days: Int = 30,
        @Header("X-API-Key") apiKey: String
    ): Map<String, Any>

    @GET("api/v1/aqi-reference")
    suspend fun getAqiReference(): Map<String, Any>

    @GET("api/v1/pollution-info")
    suspend fun getPollutionInfo(
        @Query("pollutant") pollutant: String,
        @Header("X-API-Key") apiKey: String
    ): Map<String, Any>

    @GET("api/v1/health")
    suspend fun checkHealth(): Map<String, Any>

    @GET("api/v1/info")
    suspend fun getInfo(): Map<String, Any>

    @Multipart
    @POST("api/v1/detect")
    suspend fun detectObjects(
        @Part file: MultipartBody.Part,
        @Query("confidence") confidence: Float = 0.5f,
        @Header("X-API-Key") apiKey: String
    ): Map<String, Any>

    @GET("api/v1/monitor/cache-stats")
    suspend fun getCacheStats(
        @Header("X-API-Key") apiKey: String
    ): Map<String, Any>

    @GET("api/v1/monitor/performance")
    suspend fun getPerformanceStats(
        @Header("X-API-Key") apiKey: String
    ): Map<String, Any>
}
