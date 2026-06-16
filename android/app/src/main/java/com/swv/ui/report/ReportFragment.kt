package com.swv.ui.report

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.DialogFragment
import androidx.fragment.app.FragmentManager
import com.swv.R
import com.swv.api.models.EnvironmentalReport
import com.swv.api.models.PollutantReading

class ReportFragment : DialogFragment() {

    private var report: EnvironmentalReport? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setStyle(STYLE_NORMAL, R.style.Theme_SWV)
    }

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_report_detail, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        report?.let { bindReport(it, view) }
    }

    private fun bindReport(report: EnvironmentalReport, view: View) {
        view.findViewById<TextView>(R.id.tv_detail_report_id).text = report.reportId
        view.findViewById<TextView>(R.id.tv_detail_timestamp).text = report.timestamp.take(19).replace("T", " ")

        val location = report.location
        val locStr = buildString {
            append(location.city ?: "")
            if (location.region != null) append(", ${location.region}")
            if (location.country != null) append(", ${location.country}")
            if (isEmpty()) append("${location.latitude}, ${location.longitude}")
        }
        view.findViewById<TextView>(R.id.tv_detail_location).text = locStr

        view.findViewById<TextView>(R.id.tv_detail_aqi).text = "AQI: ${report.airQualitySummary.aqiValue}"
        view.findViewById<TextView>(R.id.tv_detail_primary_pollutant).text = "Primary: ${report.airQualitySummary.primaryPollutant}"
        view.findViewById<TextView>(R.id.tv_detail_smoke).text = "Smoke: ${report.smokeAnalysis.smokePercentage}% (${report.smokeAnalysis.smokeLevel})"
        view.findViewById<TextView>(R.id.tv_detail_risk).text = report.riskAssessment

        val env = report.environmentalData
        val envStr = buildString {
            env?.temperature?.let { append("Temp: ${it}°C  ") }
            env?.humidity?.let { append("Humidity: ${it}%  ") }
            env?.windSpeed?.let { append("Wind: ${it}m/s") }
        }
        view.findViewById<TextView>(R.id.tv_detail_environmental).text = envStr.ifEmpty { "No environmental data" }

        val pollutants = report.pollutantReadings
        val polStr = pollutants?.joinToString("\n") { p ->
            "${p.pollutantType}: ${p.value} ${p.unit} (AQI: ${p.aqiIndex}, ${p.riskLevel})"
        } ?: "No pollutant data"
        view.findViewById<TextView>(R.id.tv_detail_pollutants).text = polStr

        val recs = report.recommendations?.joinToString("\n• ") { it } ?: ""
        view.findViewById<TextView>(R.id.tv_detail_recommendations).text = if (recs.isNotEmpty()) "• $recs" else "No recommendations"

        view.findViewById<TextView>(R.id.tv_detail_recommendation_text).text = report.airQualitySummary.healthRecommendation

        view.findViewById<View>(R.id.btn_close).setOnClickListener { dismiss() }
    }

    companion object {
        private const val ARG_REPORT = "report"

        fun show(manager: FragmentManager, report: EnvironmentalReport) {
            val fragment = ReportFragment().apply {
                arguments = Bundle().apply {
                    putSerializable(ARG_REPORT, report as java.io.Serializable)
                }
            }
            fragment.show(manager, "report_detail")
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        outState.putSerializable(ARG_REPORT, report)
    }
}
