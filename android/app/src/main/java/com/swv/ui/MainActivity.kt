package com.swv.ui

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.Toolbar
import com.google.android.material.button.MaterialButton
import com.swv.R
import com.swv.ui.camera.CaptureActivity
import com.swv.ui.dashboard.DashboardActivity
import com.swv.ui.report.ReportActivity
import com.swv.utils.PermissionUtils

class MainActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val toolbar: Toolbar = findViewById(R.id.toolbar)
        setSupportActionBar(toolbar)
        supportActionBar?.title = getString(R.string.app_name)

        findViewById<MaterialButton>(R.id.btn_analyze).setOnClickListener {
            if (PermissionUtils.hasCameraPermission(this)) {
                startActivity(Intent(this, CaptureActivity::class.java))
            } else {
                PermissionUtils.requestCameraPermission(this)
            }
        }

        findViewById<MaterialButton>(R.id.btn_dashboard).setOnClickListener {
            startActivity(Intent(this, DashboardActivity::class.java))
        }

        findViewById<MaterialButton>(R.id.btn_reports).setOnClickListener {
            startActivity(Intent(this, ReportActivity::class.java))
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (PermissionUtils.allPermissionsGranted(grantResults)) {
            startActivity(Intent(this, CaptureActivity::class.java))
        } else {
            Toast.makeText(this, "Camera permission required", Toast.LENGTH_SHORT).show()
        }
    }
}
