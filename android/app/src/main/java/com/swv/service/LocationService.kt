package com.swv.service

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.location.Address
import android.location.Geocoder
import android.os.Handler
import android.os.Looper
import com.google.android.gms.location.*
import com.google.android.gms.tasks.Task
import com.swv.api.models.GeoLocation
import com.swv.utils.Constants
import com.swv.utils.PermissionUtils
import java.util.Locale
import java.util.concurrent.Executors

class LocationService(private val context: Context) {

    private val backgroundExecutor = Executors.newSingleThreadExecutor()
    private val mainHandler = Handler(Looper.getMainLooper())

    private val fusedLocationClient: FusedLocationProviderClient =
        LocationServices.getFusedLocationProviderClient(context)

    private val locationRequest: LocationRequest = LocationRequest.Builder(
        Priority.PRIORITY_HIGH_ACCURACY,
        Constants.LOCATION_UPDATE_INTERVAL_MS
    ).apply {
        setMinUpdateIntervalMillis(Constants.LOCATION_FASTEST_INTERVAL_MS)
    }.build()

    private val locationCallback: LocationCallback = object : LocationCallback() {
        override fun onLocationResult(locationResult: LocationResult) {
            locationResult.lastLocation?.let { location ->
                lastKnownLocation = GeoLocation(
                    latitude = location.latitude,
                    longitude = location.longitude,
                    accuracyMeters = location.accuracy.toDouble()
                )
            }
        }
    }

    var lastKnownLocation: GeoLocation? = null
        private set

    @SuppressLint("MissingPermission")
    fun getCurrentLocation(callback: (GeoLocation?) -> Unit) {
        if (!PermissionUtils.hasLocationPermission(context)) {
            callback(null)
            return
        }

        fusedLocationClient.lastLocation
            .addOnSuccessListener { location ->
                if (location != null) {
                    val geoLocation = GeoLocation(
                        latitude = location.latitude,
                        longitude = location.longitude,
                        accuracyMeters = location.accuracy.toDouble()
                    )
                    lastKnownLocation = geoLocation
                    resolveAddress(geoLocation, callback)
                } else {
                    requestNewLocation(callback)
                }
            }
            .addOnFailureListener {
                callback(null)
            }
    }

    @SuppressLint("MissingPermission")
    private fun requestNewLocation(callback: (GeoLocation?) -> Unit) {
        try {
            fusedLocationClient.requestLocationUpdates(
                locationRequest,
                locationCallback,
                Looper.getMainLooper()
            ).addOnCompleteListener { task ->
                stopLocationUpdates()
                val loc = lastKnownLocation
                if (task.isSuccessful && loc != null) {
                    resolveAddress(loc, callback)
                } else {
                    callback(lastKnownLocation)
                }
            }
        } catch (e: SecurityException) {
            callback(null)
        }
    }

    private fun resolveAddress(geoLocation: GeoLocation, callback: (GeoLocation) -> Unit) {
        backgroundExecutor.execute {
            try {
                val geocoder = Geocoder(context, Locale.getDefault())
                val addresses: List<Address>? = geocoder.getFromLocation(
                    geoLocation.latitude,
                    geoLocation.longitude,
                    1
                )
                val enriched = if (!addresses.isNullOrEmpty()) {
                    val addr = addresses[0]
                    geoLocation.copy(
                        address = addr.getAddressLine(0),
                        country = addr.countryName,
                        region = addr.adminArea,
                        city = addr.locality
                    )
                } else {
                    geoLocation
                }
                mainHandler.post { callback(enriched) }
            } catch (e: Exception) {
                mainHandler.post { callback(geoLocation) }
            }
        }
    }

    fun stopLocationUpdates() {
        try {
            fusedLocationClient.removeLocationUpdates(locationCallback)
        } catch (e: Exception) {
            // ignore
        }
    }
}
