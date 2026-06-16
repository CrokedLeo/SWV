package com.swv.api

import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import com.swv.utils.Constants
import java.util.concurrent.TimeUnit

object ApiClient {

    private var baseUrl: String = Constants.API_BASE_URL
    private var apiKey: String = Constants.API_KEY

    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = if (Constants.LOG_ENABLED) {
            HttpLoggingInterceptor.Level.BODY
        } else {
            HttpLoggingInterceptor.Level.NONE
        }
    }

    private val okHttpClient: OkHttpClient by lazy {
        OkHttpClient.Builder()
            .connectTimeout(Constants.CONNECT_TIMEOUT_SECONDS, TimeUnit.SECONDS)
            .readTimeout(Constants.READ_TIMEOUT_SECONDS, TimeUnit.SECONDS)
            .writeTimeout(Constants.WRITE_TIMEOUT_SECONDS, TimeUnit.SECONDS)
            .addInterceptor(loggingInterceptor)
            .addInterceptor { chain ->
                val request = chain.request().newBuilder()
                    .addHeader("X-API-Key", apiKey)
                    .build()
                chain.proceed(request)
            }
            .build()
    }

    private val retrofit: Retrofit by lazy {
        Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }

    private val apiService: ApiService by lazy {
        retrofit.create(ApiService::class.java)
    }

    fun getApiService(): ApiService = apiService

    fun updateConfig(newBaseUrl: String, newApiKey: String) {
        baseUrl = newBaseUrl
        apiKey = newApiKey
    }

    fun getBaseUrl(): String = baseUrl
    fun getApiKey(): String = apiKey
}
