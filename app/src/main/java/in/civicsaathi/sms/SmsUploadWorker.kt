package `in`.civicsaathi.sms

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import `in`.civicsaathi.api.ApiClient
import `in`.civicsaathi.api.AppPrefs
import `in`.civicsaathi.api.SmsPayload
import `in`.civicsaathi.notify.NotificationHelper
import kotlinx.coroutines.delay

class SmsUploadWorker(
    appContext: Context,
    params: WorkerParameters
) : CoroutineWorker(appContext, params) {

    override suspend fun doWork(): Result {
        val sender = inputData.getString("sender") ?: return Result.failure()
        val text = inputData.getString("text") ?: return Result.failure()
        val receivedAt = inputData.getString("received_at") ?: return Result.failure()

        return try {
            val userId = AppPrefs.getUserId(applicationContext)
            val api = ApiClient.create(AppPrefs.getBaseUrl(applicationContext))

            api.postSms(SmsPayload(userId, sender, text, receivedAt))
            delay(5000) // Give Person 1's background watcher ~5s to process

            val unread = api.getNotifications(userId, unread = true)
            unread.forEach { NotificationHelper.showNotification(applicationContext, it) }
            Result.success()
        } catch (_: Exception) {
            Result.retry()
        }
    }
}