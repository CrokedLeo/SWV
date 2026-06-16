package com.swv.ui.report

import android.os.Bundle
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.Toolbar
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.swv.R
import com.swv.api.ApiClient
import com.swv.api.models.EnvironmentalReport
import com.swv.service.CacheManager
import com.swv.service.LocationService
import kotlinx.coroutines.*
import timber.log.Timber

class ReportActivity : AppCompatActivity() {

    private lateinit var recyclerView: RecyclerView
    private lateinit var reportAdapter: ReportAdapter
    private lateinit var cacheManager: CacheManager
    private lateinit var locationService: LocationService
    private lateinit var tvEmpty: TextView
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var reports: List<EnvironmentalReport> = emptyList()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_report)

        val toolbar: Toolbar = findViewById(R.id.toolbar)
        setSupportActionBar(toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        supportActionBar?.title = "Reports"

        cacheManager = CacheManager(this)
        locationService = LocationService(this)
        tvEmpty = findViewById(R.id.tv_empty)

        recyclerView = findViewById(R.id.recycler_reports)
        recyclerView.layoutManager = LinearLayoutManager(this)
        reportAdapter = ReportAdapter { report ->
            ReportFragment.show(supportFragmentManager, report)
        }
        recyclerView.adapter = reportAdapter
    }

    override fun onResume() {
        super.onResume()
        loadReports()
    }

    private fun loadReports() {
        scope.launch {
            val cached = cacheManager.getCachedReports()
            reports = cached
            withContext(Dispatchers.Main) {
                if (cached.isEmpty()) {
                    tvEmpty.visibility = android.view.View.VISIBLE
                    recyclerView.visibility = android.view.View.GONE
                } else {
                    tvEmpty.visibility = android.view.View.GONE
                    recyclerView.visibility = android.view.View.VISIBLE
                    reportAdapter.submitList(cached)
                }
            }

            locationService.getCurrentLocation { geoLocation ->
                if (geoLocation != null) {
                    scope.launch {
                        try {
                            val api = ApiClient.getApiService()
                            val remote = api.getReportsHistory(
                                latitude = geoLocation.latitude,
                                longitude = geoLocation.longitude,
                                apiKey = ApiClient.getApiKey()
                            )
                            Timber.d("Remote reports: $remote")
                        } catch (e: Exception) {
                            Timber.e(e, "Failed to fetch remote reports")
                        }
                    }
                }
            }
        }
    }

    override fun onSupportNavigateUp(): Boolean {
        onBackPressed()
        return true
    }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }
}
