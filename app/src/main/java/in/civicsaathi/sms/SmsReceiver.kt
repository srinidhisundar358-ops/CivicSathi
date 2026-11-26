package `in`.civicsaathi.sms

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.provider.Telephony
import androidx.work.*
import org.json.JSONObject
import java.time.Instant
import java.util.concurrent.TimeUnit

class SmsReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Telephony.Sms.Intents.SMS_RECEIVED_ACTION) return
        val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent)
        if (messages.isEmpty()) return

        val sender = messages[0].originatingAddress ?: return
        val fullText = messages.joinToString("") { it.messageBody ?: "" }

        // 1. Immediately drop OTPs on the phone
        val otpRegex = Regex("""(?i)\b(otp|one[\s-]?time[\s-]?password|verification\s+code)\b.*\b\d{4,8}\b""")
        if (otpRegex.containsMatchIn(fullText)) return

        // 2. Check government sender header or demo number from assets/gov_senders.json
        if (!isGovernmentSender(context, sender)) return

        val workData = workDataOf(
            "sender" to sender,
            "text" to fullText,
            "received_at" to Instant.now().toString()
        )

        val request = OneTimeWorkRequestBuilder<SmsUploadWorker>()
            .setInputData(workData)
            .setConstraints(
                Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build()
            )
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 5, TimeUnit.SECONDS)
            .build()

        WorkManager.getInstance(context).enqueue(request)
    }

    private fun isGovernmentSender(context: Context, rawSender: String): Boolean {
        return try {
            val jsonStr = context.assets.open("gov_senders.json").bufferedReader().use { it.readText() }
            val json = JSONObject(jsonStr)
            val headers = json.getJSONArray("sms_headers")
            val demoNumbers = json.getJSONArray("demo_numbers")

            val clean = rawSender.trim()
            for (i in 0 until demoNumbers.length()) {
                if (clean.endsWith(demoNumbers.getString(i).takeLast(10))) return true
            }

            // Strip "XX-" prefix and optional "-G/-S/-T/-P" suffix
            val normalized = clean
                .replace(Regex("^[A-Za-z]{2}-"), "")
                .replace(Regex("-[GSTP]$", RegexOption.IGNORE_CASE), "")
                .uppercase()

            for (i in 0 until headers.length()) {
                if (normalized.contains(headers.getString(i).uppercase())) return true
            }
            false
        } catch (_: Exception) {
            false
        }
    }
}