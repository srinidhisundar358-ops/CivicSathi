package `in`.civicsaathi.api

import android.content.Context

object AppPrefs {
    private const val PREFS = "civicsaathi_prefs"

    fun getBaseUrl(context: Context): String =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString("base_url", "http://10.0.2.2:8000") ?: "http://10.0.2.2:8000"

    fun setBaseUrl(context: Context, url: String) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString("base_url", url.trim()).apply()
    }

    fun getUserId(context: Context): String =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString("user_id", "demo_ravi") ?: "demo_ravi"

    fun setUserId(context: Context, userId: String) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString("user_id", userId).apply()
    }

    fun isUseFake(context: Context): Boolean =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getBoolean("use_fake", false)

    fun setUseFake(context: Context, fake: Boolean) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putBoolean("use_fake", fake).apply()
    }
}

interface CivicRepository {
    suspend fun getProfile(userId: String): UserProfile
    suspend fun saveProfile(profile: UserProfile): UserProfile
    suspend fun sendChat(userId: String, message: String, contextId: String? = null): ChatResponse
    suspend fun getNotifications(userId: String, unreadOnly: Boolean = true): List<NotificationItem>
    suspend fun markRead(notificationId: String)
    suspend fun startDigiLocker(userId: String): String
    suspend fun getForm(formId: String): PrefilledForm
    suspend fun saveForm(form: PrefilledForm): PrefilledForm
    suspend fun confirmForm(formId: String): FormConfirmResponse
    suspend fun simulateSms(userId: String, sampleIndex: Int = 0)
}

class RealRepository(private val api: CivicSathiApi) : CivicRepository {
    override suspend fun getProfile(userId: String) = api.getProfile(userId)
    override suspend fun saveProfile(profile: UserProfile) = api.putProfile(profile.userId, profile)
    override suspend fun sendChat(userId: String, message: String, contextId: String?) =
        api.chat(ChatRequest(userId, message, contextId))
    override suspend fun getNotifications(userId: String, unreadOnly: Boolean) =
        api.getNotifications(userId, unreadOnly)
    override suspend fun markRead(notificationId: String) { api.markNotificationRead(notificationId) }
    override suspend fun startDigiLocker(userId: String) =
        api.connectStart("digilocker", userId).url ?: ""
    override suspend fun getForm(formId: String) = api.getForm(formId)
    override suspend fun saveForm(form: PrefilledForm) = api.putForm(form.formId, form)
    override suspend fun confirmForm(formId: String) = api.confirmForm(formId)
    override suspend fun simulateSms(userId: String, sampleIndex: Int) {
        api.simulateSms(SimulateSmsRequest(userId, sampleIndex))
    }
}

class FakeRepository : CivicRepository {
    private val profiles = mutableMapOf(
        "demo_ravi" to UserProfile(
            userId = "demo_ravi",
            language = "en",
            age = 29,
            birthState = "karnataka",
            currentState = "karnataka",
            personal = PersonalDetails(
                fullName = "Ravi Kumar",
                dob = "1997-04-12",
                address = Address("14 MG Road", "Bengaluru", "Bengaluru Urban", "karnataka", "560001")
            ),
            documents = listOf(
                HeldDocument("aadhaar", "karnataka", "karnataka", null, "digilocker"),
                HeldDocument("voter_id", "karnataka", "karnataka", null, "digilocker"),
                HeldDocument("driving_licence", "karnataka", "karnataka", "2027-01-05", "digilocker"),
                HeldDocument("vehicle_rc", "karnataka", "karnataka", null, "user")
            ),
            consents = Consents(sms = true, gmail = false, digilocker = true)
        ),
        "demo_ajji" to UserProfile(
            userId = "demo_ajji",
            language = "kn",
            age = 74,
            birthState = "karnataka",
            currentState = "karnataka",
            personal = PersonalDetails(
                fullName = "Shantamma",
                dob = "1952-08-19",
                address = Address("22 Saraswathipuram", "Mysuru", "Mysuru", "karnataka", "570009")
            ),
            documents = listOf(
                HeldDocument("aadhaar", "karnataka", "karnataka", null, "digilocker"),
                HeldDocument("pension_ppo", "karnataka", "karnataka", "2026-11-30", "user")
            ),
            consents = Consents(sms = true)
        )
    )

    private val notifications = mutableListOf(
        NotificationItem(
            notificationId = "notif_1",
            userId = "demo_ravi",
            title = "Driving Licence Expiring Soon",
            body = "Your Karnataka DL expires on 05 Jan 2027. Renew before expiry.",
            type = "reminder",
            openTarget = "chat",
            contextId = "msg_dl_1",
            createdAt = "2026-11-26T10:00:00Z",
            read = false
        ),
        NotificationItem(
            notificationId = "notif_2",
            userId = "demo_ravi",
            title = "Voter Shift Form Pre-filled",
            body = "Form 8 is ready for review before shifting to Pune.",
            type = "form_ready",
            openTarget = "form",
            contextId = "form_voter_1",
            createdAt = "2026-11-26T10:05:00Z",
            read = false
        )
    )

    private var form = PrefilledForm(
        formId = "form_voter_1",
        userId = "demo_ravi",
        serviceId = "voter_shift",
        state = "maharashtra",
        fields = listOf(
            FormField("full_name", "Full Name", "Ravi Kumar", "digilocker", true, false),
            FormField("epic_number", "EPIC / Voter ID Number (Sensitive)", null, "user", true, true),
            FormField("new_address", "New Pune Address", "Flat 4B, Kothrud, Pune, Maharashtra", "profile", true, false),
            FormField("pincode", "Pincode", "411038", "profile", true, false)
        ),
        missing = listOf("epic_number"),
        officialLink = "https://voters.eci.gov.in/",
        status = "draft"
    )

    override suspend fun getProfile(userId: String) = profiles[userId] ?: profiles["demo_ravi"]!!
    override suspend fun saveProfile(profile: UserProfile): UserProfile {
        profiles[profile.userId] = profile
        return profile
    }

    override suspend fun sendChat(userId: String, message: String, contextId: String?): ChatResponse {
        val plan = ActionPlan(
            summary = "Update Aadhaar address first, as Voter ID and Driving Licence require updated address proof.",
            items = listOf(
                ChecklistItem(
                    docId = "aadhaar",
                    serviceId = "aadhaar_address_update",
                    action = "Update Aadhaar Address to Pune",
                    priority = "mandatory",
                    reason = "Required first as proof of address for downstream updates.",
                    steps = listOf("Log in to myAadhaar portal", "Upload Pune rent agreement or utility bill", "Submit SRN"),
                    requiredDocs = listOf("Proof of Pune Address"),
                    fee = "Rs. 50",
                    officialLink = "https://myaadhaar.uidai.gov.in/",
                    sources = listOf(Source("UIDAI Address Update", "https://uidai.gov.in/", "2026-11-26"))
                ),
                ChecklistItem(
                    docId = "voter_id",
                    serviceId = "voter_shift",
                    action = "Shift Voter Registration (Form 8)",
                    priority = "mandatory",
                    reason = "Enroll in your new Pune assembly constituency.",
                    steps = listOf("Open ECI Voters Portal", "Fill Form 8 for shifting residence", "Attach updated Aadhaar"),
                    requiredDocs = listOf("aadhaar"),
                    fee = "Free",
                    officialLink = "https://voters.eci.gov.in/",
                    sources = listOf(Source("ECI Form 8", "https://voters.eci.gov.in/", "2026-11-26"))
                )
            )
        )
        return ChatResponse(
            reply = "Here is your step-by-step relocation checklist from Karnataka to Maharashtra:",
            plan = plan,
            conversationId = "conv_demo_1"
        )
    }

    override suspend fun getNotifications(userId: String, unreadOnly: Boolean) =
        notifications.filter { it.userId == userId && (!unreadOnly || !it.read) }

    override suspend fun markRead(notificationId: String) {
        val idx = notifications.indexOfFirst { it.notificationId == notificationId }
        if (idx >= 0) notifications[idx] = notifications[idx].copy(read = true)
    }

    override suspend fun startDigiLocker(userId: String) = "civicsaathi://connected?source=digilocker"
    override suspend fun getForm(formId: String) = form
    override suspend fun saveForm(form: PrefilledForm): PrefilledForm {
        this.form = form
        return form
    }

    override suspend fun confirmForm(formId: String) =
        FormConfirmResponse("http://10.0.2.2:8000/files/$formId.pdf", form.officialLink)

    override suspend fun simulateSms(userId: String, sampleIndex: Int) {
        notifications.add(
            0,
            NotificationItem(
                notificationId = "notif_sim_${System.currentTimeMillis()}",
                userId = userId,
                title = "Simulated Govt SMS Alert",
                body = "Action required on your document. Tap to review.",
                type = "reminder",
                openTarget = "chat",
                contextId = "msg_sim_1",
                createdAt = "2026-11-26T18:00:00Z",
                read = false
            )
        )
    }
}