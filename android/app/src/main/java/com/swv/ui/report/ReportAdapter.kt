package com.swv.ui.report

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.cardview.widget.CardView
import androidx.recyclerview.widget.RecyclerView
import com.swv.R
import com.swv.api.models.EnvironmentalReport
import java.text.SimpleDateFormat
import java.util.Locale

class ReportAdapter(
    private val onItemClick: (EnvironmentalReport) -> Unit
) : RecyclerView.Adapter<ReportAdapter.ReportViewHolder>() {

    private var reports: List<EnvironmentalReport> = emptyList()

    fun submitList(list: List<EnvironmentalReport>) {
        reports = list
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ReportViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_report, parent, false)
        return ReportViewHolder(view)
    }

    override fun onBindViewHolder(holder: ReportViewHolder, position: Int) {
        holder.bind(reports[position])
    }

    override fun getItemCount(): Int = reports.size

    inner class ReportViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val card: CardView = itemView.findViewById(R.id.card_report)
        private val tvReportId: TextView = itemView.findViewById(R.id.tv_report_id)
        private val tvLocation: TextView = itemView.findViewById(R.id.tv_location)
        private val tvDate: TextView = itemView.findViewById(R.id.tv_date)
        private val tvAqi: TextView = itemView.findViewById(R.id.tv_aqi_value)
        private val tvSmoke: TextView = itemView.findViewById(R.id.tv_smoke_percent)
        private val tvRisk: TextView = itemView.findViewById(R.id.tv_risk_level)

        fun bind(report: EnvironmentalReport) {
            tvReportId.text = report.reportId
            tvLocation.text = report.location.city ?: report.location.address ?: "${report.location.latitude}, ${report.location.longitude}"
            tvAqi.text = "AQI: ${report.airQualitySummary.aqiValue}"
            tvSmoke.text = "Smoke: ${report.smokeAnalysis.smokePercentage}%"
            tvRisk.text = report.riskAssessment.take(100)
            tvDate.text = report.timestamp.take(19).replace("T", " ")

            card.setOnClickListener { onItemClick(report) }
        }
    }
}
