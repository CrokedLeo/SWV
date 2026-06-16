package com.swv.ui.dashboard

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.Toolbar
import com.swv.R
import com.swv.service.LocationService
import com.swv.utils.Constants

class MapViewActivity : AppCompatActivity() {

    private lateinit var locationService: LocationService

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_dashboard)

        val toolbar: Toolbar = findViewById(R.id.toolbar)
        setSupportActionBar(toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        supportActionBar?.title = "Map View"

        locationService = LocationService(this)

        findViewById<TextView>(R.id.tv_dashboard_map_label).text = "Opening map..."

        locationService.getCurrentLocation { geoLocation ->
            if (geoLocation != null) {
                openInGoogleMaps(geoLocation.latitude, geoLocation.longitude)
            } else {
                Toast.makeText(this, "Unable to get location", Toast.LENGTH_SHORT).show()
                openInGoogleMaps(0.0, 0.0)
            }
        }
    }

    private fun openInGoogleMaps(lat: Double, lon: Double) {
        val uri = Uri.parse("geo:$lat,$lon?z=${Constants.MAP_DEFAULT_ZOOM.toInt()}")
        val intent = Intent(Intent.ACTION_VIEW, uri).apply {
            setPackage("com.google.android.apps.maps")
        }
        try {
            startActivity(intent)
        } catch (e: Exception) {
            val webUri = Uri.parse("https://maps.google.com/maps?q=$lat,$lon&z=${Constants.MAP_DEFAULT_ZOOM.toInt()}")
            startActivity(Intent(Intent.ACTION_VIEW, webUri))
        }
        finish()
    }

    override fun onSupportNavigateUp(): Boolean {
        onBackPressed()
        return true
    }
}
