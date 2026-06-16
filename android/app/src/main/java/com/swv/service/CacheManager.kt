package com.swv.service

import android.content.Context
import android.content.SharedPreferences
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import com.swv.api.models.EnvironmentalReport
import com.swv.utils.Constants

class CacheManager(private val context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences(Constants.CACHE_NAME, Context.MODE_PRIVATE)
    private val gson = Gson()

    fun cacheReport(report: EnvironmentalReport) {
        val reports = getCachedReports().toMutableList()
        reports.add(0, report)

        val trimmed = if (reports.size > Constants.CACHE_MAX_SIZE) {
            reports.take(Constants.CACHE_MAX_SIZE)
        } else {
            reports
        }

        val json = gson.toJson(trimmed)
        prefs.edit().putString(KEY_CACHED_REPORTS, json).apply()
    }

    fun getCachedReports(): List<EnvironmentalReport> {
        val json = prefs.getString(KEY_CACHED_REPORTS, null) ?: return emptyList()
        return try {
            val type = object : TypeToken<List<EnvironmentalReport>>() {}.type
            gson.fromJson(json, type) ?: emptyList()
        } catch (e: Exception) {
            emptyList()
        }
    }

    fun getReportById(reportId: String): EnvironmentalReport? {
        return getCachedReports().find { it.reportId == reportId }
    }

    fun clearCache() {
        prefs.edit().remove(KEY_CACHED_REPORTS).apply()
    }

    fun getCacheSize(): Int = getCachedReports().size

    fun saveString(key: String, value: String) {
        prefs.edit().putString(key, value).apply()
    }

    fun getString(key: String, default: String = ""): String {
        return prefs.getString(key, default) ?: default
    }

    fun saveFloat(key: String, value: Float) {
        prefs.edit().putFloat(key, value).apply()
    }

    fun getFloat(key: String, default: Float = 0f): Float {
        return prefs.getFloat(key, default)
    }

    companion object {
        private const val KEY_CACHED_REPORTS = "cached_reports"
    }
}
