package `in`.civicsaathi.api

import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.http.*
import java.util.concurrent.TimeUnit

interface CivicSathiApi {
    @GET("health")
    suspend fun health(): Map<String, String>

    @POST("chat")
    suspend fun chat(@Body body: ChatRequest): ChatResponse

    @GET("profile/{userId}")
    suspend fun getProfile(@Path("userId") userId: String): UserProfile

    @PUT("profile/{userId}")
    suspend fun putProfile(@Path("userId") userId: String, @Body profile: UserProfile): UserProfile

    @GET("connect/{source}/start")
    suspend fun connectStart(
        @Path("source") source: String,
        @Query("user_id") userId: String
    ): ConnectStartResponse

    @POST("connect/{source}/revoke")
    suspend fun connectRevoke(
        @Path("source") source: String,
        @Query("user_id") userId: String
    ): Map<String, Boolean>

    @POST("inbox/sms")
    suspend fun postSms(@Body body: SmsPayload): Response<Unit>

    @GET("notifications/{userId}")
    suspend fun getNotifications(
        @Path("userId") userId: String,
        @Query("unread") unread: Boolean = true
    ): List<NotificationItem>

    @POST("notifications/{id}/read")
    suspend fun markNotificationRead(@Path("id") id: String): Map<String, Boolean>

    @GET("forms/{formId}")
    suspend fun getForm(@Path("formId") formId: String): PrefilledForm

    @PUT("forms/{formId}")
    suspend fun putForm(@Path("formId") formId: String, @Body form: PrefilledForm): PrefilledForm

    @POST("forms/{formId}/confirm")
    suspend fun confirmForm(@Path("formId") formId: String): FormConfirmResponse

    @POST("demo/simulate-sms")
    suspend fun simulateSms(@Body body: SimulateSmsRequest): Map<String, String>
}

object ApiClient {
    private val json = Json {
        ignoreUnknownKeys = true
        encodeDefaults = true
        isLenient = true
    }

    private val okHttp = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(20, TimeUnit.SECONDS)
        .writeTimeout(20, TimeUnit.SECONDS)
        .build()

    fun create(baseUrl: String): CivicSathiApi {
        val cleanUrl = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"
        return Retrofit.Builder()
            .baseUrl(cleanUrl)
            .client(okHttp)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()
            .create(CivicSathiApi::class.java)
    }
}