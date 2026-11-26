package `in`.civicsaathi.api

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class Source(
    val title: String,
    val url: String,
    @SerialName("last_verified") val lastVerified: String
)

@Serializable
data class Address(
    val line1: String,
    val city: String,
    val district: String? = null,
    val state: String,
    val pincode: String
)

@Serializable
data class PersonalDetails(
    @SerialName("full_name") val fullName: String,
    val dob: String? = null,
    @SerialName("relative_name") val relativeName: String? = null,
    val phone: String? = null,
    val email: String? = null,
    val address: Address? = null
)

@Serializable
data class HeldDocument(
    @SerialName("doc_id") val docId: String,
    @SerialName("issued_state") val issuedState: String? = null,
    @SerialName("address_state") val addressState: String? = null,
    @SerialName("expiry_date") val expiryDate: String? = null,
    val origin: String = "user"
)

@Serializable
data class Consents(
    val sms: Boolean = false,
    val gmail: Boolean = false,
    val digilocker: Boolean = false
)

@Serializable
data class UserProfile(
    @SerialName("user_id") val userId: String,
    val language: String = "en",
    val age: Int? = null,
    @SerialName("birth_state") val birthState: String? = null,
    @SerialName("current_state") val currentState: String,
    val personal: PersonalDetails? = null,
    val documents: List<HeldDocument> = emptyList(),
    val consents: Consents = Consents()
)

@Serializable
data class ChecklistItem(
    @SerialName("doc_id") val docId: String,
    @SerialName("service_id") val serviceId: String,
    val action: String,
    val priority: String,
    val reason: String,
    val steps: List<String> = emptyList(),
    @SerialName("required_docs") val requiredDocs: List<String> = emptyList(),
    val fee: String? = null,
    @SerialName("official_link") val officialLink: String? = null,
    val deadline: String? = null,
    val sources: List<Source> = emptyList()
)

@Serializable
data class ActionPlan(
    val summary: String,
    val items: List<ChecklistItem> = emptyList(),
    @SerialName("reminders_created") val remindersCreated: List<String> = emptyList()
)

@Serializable
data class NotificationItem(
    @SerialName("notification_id") val notificationId: String,
    @SerialName("user_id") val userId: String,
    val title: String,
    val body: String,
    val type: String,
    @SerialName("open_target") val openTarget: String,
    @SerialName("context_id") val contextId: String? = null,
    @SerialName("created_at") val createdAt: String,
    val read: Boolean = false
)

@Serializable
data class FormField(
    @SerialName("field_id") val fieldId: String,
    val label: String,
    val value: String? = null,
    val source: String = "profile",
    val required: Boolean = true,
    @SerialName("needs_user_input") val needsUserInput: Boolean = false
)

@Serializable
data class PrefilledForm(
    @SerialName("form_id") val formId: String,
    @SerialName("user_id") val userId: String,
    @SerialName("service_id") val serviceId: String,
    val state: String,
    val fields: List<FormField> = emptyList(),
    val missing: List<String> = emptyList(),
    @SerialName("official_link") val officialLink: String,
    val status: String = "draft"
)

// Request & Response DTOs
@Serializable
data class ChatRequest(
    @SerialName("user_id") val userId: String,
    val message: String,
    @SerialName("context_id") val contextId: String? = null
)

@Serializable
data class ChatResponse(
    val reply: String,
    val plan: ActionPlan? = null,
    @SerialName("conversation_id") val conversationId: String
)

@Serializable
data class SmsPayload(
    @SerialName("user_id") val userId: String,
    val sender: String,
    val text: String,
    @SerialName("received_at") val receivedAt: String
)

@Serializable
data class SimulateSmsRequest(
    @SerialName("user_id") val userId: String,
    @SerialName("sample_index") val sampleIndex: Int = 0
)

@Serializable
data class ConnectStartResponse(
    val url: String? = null,
    val simulated: Boolean = false
)

@Serializable
data class FormConfirmResponse(
    @SerialName("pdf_url") val pdfUrl: String,
    @SerialName("official_link") val officialLink: String
)