package com.swv.utils

import android.Manifest
import android.app.Activity
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat

object PermissionUtils {

    private val CAMERA_PERMISSIONS = arrayOf(
        Manifest.permission.CAMERA
    )

    private val STORAGE_PERMISSIONS = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
        arrayOf(Manifest.permission.READ_MEDIA_IMAGES)
    } else {
        arrayOf(
            Manifest.permission.READ_EXTERNAL_STORAGE,
            Manifest.permission.WRITE_EXTERNAL_STORAGE
        )
    }

    private val LOCATION_PERMISSIONS = arrayOf(
        Manifest.permission.ACCESS_FINE_LOCATION,
        Manifest.permission.ACCESS_COARSE_LOCATION
    )

    fun hasCameraPermission(context: Context): Boolean {
        return CAMERA_PERMISSIONS.all {
            ContextCompat.checkSelfPermission(context, it) == PackageManager.PERMISSION_GRANTED
        }
    }

    fun hasStoragePermission(context: Context): Boolean {
        return STORAGE_PERMISSIONS.all {
            ContextCompat.checkSelfPermission(context, it) == PackageManager.PERMISSION_GRANTED
        }
    }

    fun hasLocationPermission(context: Context): Boolean {
        return LOCATION_PERMISSIONS.all {
            ContextCompat.checkSelfPermission(context, it) == PackageManager.PERMISSION_GRANTED
        }
    }

    fun requestCameraPermission(activity: Activity, requestCode: Int = Constants.REQUEST_CODE_CAMERA) {
        ActivityCompat.requestPermissions(activity, CAMERA_PERMISSIONS, requestCode)
    }

    fun requestStoragePermission(activity: Activity, requestCode: Int = Constants.REQUEST_CODE_GALLERY) {
        ActivityCompat.requestPermissions(activity, STORAGE_PERMISSIONS, requestCode)
    }

    fun requestLocationPermission(activity: Activity, requestCode: Int = Constants.REQUEST_CODE_LOCATION) {
        ActivityCompat.requestPermissions(activity, LOCATION_PERMISSIONS, requestCode)
    }

    fun allPermissionsGranted(grantResults: IntArray): Boolean {
        return grantResults.isNotEmpty() && grantResults.all { it == PackageManager.PERMISSION_GRANTED }
    }
}
