package com.sam.assistant.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.os.IBinder

/**
 * Foreground Service for Sam Android App.
 * Keeps WebSocket connection active and listens for wake words or alarm triggers in background.
 */
class SamForegroundService : Service() {

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val notification = createNotification()
        startForeground(1001, notification)
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun createNotificationChannel() {
        val channel = NotificationChannel(
            "sam_service_channel",
            "Sam Background Service",
            NotificationManager.IMPORTANCE_LOW
        )
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(channel)
    }

    private fun createNotification(): Notification {
        return Notification.Builder(this, "sam_service_channel")
            .setContentTitle("Sam AI Assistant")
            .setContentText("Connected and listening in background...")
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .build()
    }
}
