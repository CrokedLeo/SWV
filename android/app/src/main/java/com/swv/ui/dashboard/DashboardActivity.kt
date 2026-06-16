package com.swv.ui.dashboard

import android.content.Intent
import android.os.Bundle
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.Toolbar
import androidx.cardview.widget.CardView
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout
import com.google.android.material.button.MaterialButton
import com.swv.R
import com.swv.api.ApiClient
import com.swv.api.models.EnvironmentalReport
import com.swv.service.CacheManager
import com.swv.service.LocationService
import com.swv.ui.camera.CaptureActivity
import kotlinx.coroutines.*
import timber.log.Timber

class DashboardActivity : AppCompatActivity() {

    private lateinit var swipeRefresh: SwipeRefreshLayout
    private lateinit var tvAqi: TextView
    private lateinit var tvSmoke: TextView
    private lateinit var tvLocation: TextView
    private lateinit var tvRecommendation: TextView
    private lateinit var tvReportCount: TextView
    private lateinit var tvLatestReportId: TextView
    private lateinit var cacheManager: CacheManager
    private lateinit var locationService: LocationService
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_dashboard)

        val toolbar: Toolbar = findViewById(R.id.toolbar)
        setSupportActionBar(toolbar)
        supportActionBar?.title = "Dashboard"

        cacheManager = CacheManager(this)
        locationService = LocationService(this)

        tvAqi = findViewById(R.id.tv_dashboard_aqi)
        tvSmoke = findViewById(R.id.tv_dashboard_smoke)
        tvLocation = findViewById(R.id.tv_dashboard_location)
        tvRecommendation = findViewById(R.id.tv_dashboard_recommendation)
        tvReportCount = findViewById(R.id.tv_dashboard_report_count)
        tvLatestReportId = findViewById(R.id.tv_dashboard_latest_report)

        swipeRefresh = findViewById(R.id.swipe_refresh)
        swipeRefresh.setOnRefreshListener { refreshDashboard() }

        findViewById<CardView>(R.id.card_capture).setOnClickListener {
            startActivity(Intent(this, CaptureActivity::class.java))
        }

        findViewById<CardView>(R.id.card_map).setOnClickListener {
            startActivity(Intent(this, MapViewActivity::class.java))
        }

        findViewById<CardView>(R.id.card_reports).setOnClickListener {
            startActivity(Intent(this, com.swv.ui.report.ReportActivity::class.java))
        }

        findViewById<MaterialButton>(R.id.btn_new_analysis).setOnClickListener {
            startActivity(Intent(this, CaptureActivity::class.java))
        }
    }

    override fun onResume() {
        super.onResume()
        refreshDashboard()
    }

    private fun refreshDashboard() {
        swipeRefresh.isRefreshing = true
        locationService.getCurrentLocation { geoLocation ->
            scope.launch {
                val cachedReports = cacheManager.getCachedReports()
                val latestReport = cachedReports.firstOrNull()

                withContext(Dispatchers.Main) {
                    if (geoLocation != null) {
                        val locStr = buildString {
                            append(geoLocation.city ?: "")
                            if (geoLocation.region != null) append(", ${geoLocation.region}")
                            if (isEmpty()) append("${geoLocation.latitude}, ${geoLocation.longitude}")
                        }
                        tvLocation.text = locStr
                    } else {
                        tvLocation.text = "Location unavailable"
                    }

                    tvReportCount.text = "${cachedReports.size} reports"

                    if (latestReport != null) {
                        tvAqi.text = "${latestReport.airQualitySummary.aqiValue}"
                        tvSmoke.text = "${latestReport.smokeAnalysis.smokePercentage}%"
                        tvRecommendation.text = latestReport.airQualitySummary.healthRecommendation
                        tvLatestReportId.text = latestReport.reportId
                    } else {
                        tvAqi.text = "--"
                        tvSmoke.text = "--%"
                        tvRecommendation.text = "No data yet. Capture an image to start."
                        tvLatestReportId.text = "N/A"
                    }

                    swipeRefresh.isRefreshing = false
                }

                try {
                    val api = ApiClient.getApiService()
                    val stats = api.getLocationStats(
                        latitude = geoLocation?.latitude ?: 0.0,
                        longitude = geoLocation?.longitude ?: 0.0,
                        apiKey = ApiClient.getApiKey()
                    )
                    Timber.d("Location stats: $stats")
                } catch (e: Exception) {
                    Timber.e(e, "Failed to fetch stats")
                }
            }
        }
    }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }
}
