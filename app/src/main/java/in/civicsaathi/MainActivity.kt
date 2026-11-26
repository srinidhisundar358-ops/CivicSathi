package `in`.civicsaathi

import android.Manifest
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.browser.customtabs.CustomTabsIntent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Chat
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavHostController
import androidx.navigation.compose.*
import `in`.civicsaathi.api.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.time.temporal.ChronoUnit

class MainActivity : ComponentActivity() {
    private var deepLinkState = mutableStateOf<Triple<String, String?, String?>?>(null)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        handleIntent(intent)
        setContent {
            MaterialTheme {
                CivicSathiApp(
                    deepLink = deepLinkState.value,
                    onDeepLinkConsumed = { deepLinkState.value = null }
                )
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleIntent(intent)
    }

    private fun handleIntent(intent: Intent?) {
        intent ?: return
        // 1. DigiLocker redirect: civicsaathi://connected
        if (intent.data?.scheme == "civicsaathi" && intent.data?.host == "connected") {
            deepLinkState.value = Triple("home", "digilocker_connected", null)
            return
        }
        // 2. Notification tap
        val target = intent.getStringExtra("open_target") ?: return
        val contextId = intent.getStringExtra("context_id")
        val title = intent.getStringExtra("title")
        deepLinkState.value = Triple(target, contextId, title)
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CivicSathiApp(
    deepLink: Triple<String, String?, String?>?,
    onDeepLinkConsumed: () -> Unit
) {
    val context = LocalContext.current
    val navController = rememberNavController()
    val scope = rememberCoroutineScope()

    var userId by remember { mutableStateOf(AppPrefs.getUserId(context)) }
    var useFake by remember { mutableStateOf(AppPrefs.isUseFake(context)) }
    var baseUrl by remember { mutableStateOf(AppPrefs.getBaseUrl(context)) }

    val repo: CivicRepository = remember(useFake, baseUrl) {
        if (useFake) FakeRepository() else RealRepository(ApiClient.create(baseUrl))
    }

    var profile by remember { mutableStateOf<UserProfile?>(null) }
    var assistantContextId by remember { mutableStateOf<String?>(null) }
    var assistantBannerTitle by remember { mutableStateOf<String?>(null) }
    var activeFormId by remember { mutableStateOf("form_voter_1") }

    // Load profile whenever user or repo changes
    LaunchedEffect(userId, repo) {
        runCatching { profile = repo.getProfile(userId) }
    }

    // Handle deep links from notifications or DigiLocker redirect
    LaunchedEffect(deepLink) {
        deepLink?.let { (target, ctxId, title) ->
            when (target) {
                "chat" -> {
                    assistantContextId = ctxId
                    assistantBannerTitle = title
                    navController.navigate("assistant")
                }
                "form" -> {
                    if (!ctxId.isNullOrBlank()) activeFormId = ctxId
                    navController.navigate("form")
                }
                else -> {
                    runCatching { profile = repo.getProfile(userId) }
                    navController.navigate("home")
                }
            }
            onDeepLinkConsumed()
        }
    }

    val currentRoute = navController.currentBackStackEntryAsState().value?.destination?.route

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("CivicSathi", fontWeight = FontWeight.Bold) },
                actions = {
                    IconButton(onClick = { navController.navigate("home") }) {
                        Icon(Icons.Default.Home, contentDescription = "Home")
                    }
                    IconButton(onClick = { navController.navigate("settings") }) {
                        Icon(Icons.Default.Settings, contentDescription = "Settings")
                    }
                }
            )
        },
        floatingActionButton = {
            if (currentRoute != "assistant") {
                ExtendedFloatingActionButton(
                    onClick = {
                        assistantContextId = null
                        assistantBannerTitle = null
                        navController.navigate("assistant")
                    },
                    icon = { Icon(Icons.Default.Chat, contentDescription = null) },
                    text = { Text("Ask Assistant", fontSize = 16.sp) }
                )
            }
        }
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = "home",
            modifier = Modifier.padding(padding)
        ) {
            composable("onboarding") {
                OnboardingScreen(profile) { updated ->
                    scope.launch {
                        runCatching { profile = repo.saveProfile(updated) }
                        navController.navigate("consent")
                    }
                }
            }
            composable("consent") {
                ConsentScreen(
                    profile = profile,
                    onSaveConsents = { updated ->
                        scope.launch {
                            runCatching { profile = repo.saveProfile(updated) }
                            navController.navigate("home")
                        }
                    },
                    onConnectDigiLocker = {
                        scope.launch {
                            runCatching {
                                val url = repo.startDigiLocker(userId)
                                if (url.startsWith("http")) {
                                    CustomTabsIntent.Builder().build().launchUrl(context, Uri.parse(url))
                                } else {
                                    profile = repo.getProfile(userId)
                                    navController.navigate("home")
                                }
                            }
                        }
                    }
                )
            }
            composable("home") {
                HomeScreen(
                    userId = userId,
                    profile = profile,
                    repo = repo,
                    onRefreshProfile = { scope.launch { runCatching { profile = repo.getProfile(userId) } } },
                    onOpenNotification = { notif ->
                        scope.launch { runCatching { repo.markRead(notif.notificationId) } }
                        when (notif.openTarget) {
                            "form" -> {
                                if (!notif.contextId.isNullOrBlank()) activeFormId = notif.contextId
                                navController.navigate("form")
                            }
                            "chat" -> {
                                assistantContextId = notif.contextId
                                assistantBannerTitle = notif.title
                                navController.navigate("assistant")
                            }
                        }
                    },
                    onGoOnboarding = { navController.navigate("onboarding") },
                    onGoConsent = { navController.navigate("consent") }
                )
            }
            composable("assistant") {
                AssistantScreen(
                    userId = userId,
                    repo = repo,
                    contextId = assistantContextId,
                    bannerTitle = assistantBannerTitle
                )
            }
            composable("form") {
                FormReviewScreen(
                    formId = activeFormId,
                    repo = repo,
                    baseUrl = baseUrl
                )
            }
            composable("settings") {
                SettingsScreen(
                    userId = userId,
                    baseUrl = baseUrl,
                    useFake = useFake,
                    profile = profile,
                    repo = repo,
                    onUpdateSettings = { newUser, newUrl, newFake ->
                        userId = newUser
                        baseUrl = newUrl
                        useFake = newFake
                        AppPrefs.setUserId(context, newUser)
                        AppPrefs.setBaseUrl(context, newUrl)
                        AppPrefs.setUseFake(context, newFake)
                    },
                    onUpdateProfile = { updated ->
                        scope.launch { runCatching { profile = repo.saveProfile(updated) } }
                    }
                )
            }
        }
    }
}

@Composable
fun OnboardingScreen(profile: UserProfile?, onSave: (UserProfile) -> Unit) {
    var name by remember(profile) { mutableStateOf(profile?.personal?.fullName ?: "Ravi Kumar") }
    var state by remember(profile) { mutableStateOf(profile?.currentState ?: "karnataka") }
    var language by remember(profile) { mutableStateOf(profile?.language ?: "en") }
    var ageText by remember(profile) { mutableStateOf((profile?.age ?: 29).toString()) }

    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Your Civic Profile", style = MaterialTheme.typography.headlineSmall)
        OutlinedTextField(value = name, onValueChange = { name = it }, label = { Text("Full Name") }, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(value = ageText, onValueChange = { ageText = it }, label = { Text("Age") }, modifier = Modifier.fillMaxWidth())

        Text("Current State", fontWeight = FontWeight.SemiBold)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf("karnataka", "maharashtra").forEach { st ->
                FilterChip(selected = state == st, onClick = { state = st }, label = { Text(st.replaceFirstChar { it.uppercase() }) })
            }
        }

        Text("Preferred Language", fontWeight = FontWeight.SemiBold)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf("en" to "English", "hi" to "Hindi", "kn" to "Kannada", "mr" to "Marathi").forEach { (code, label) ->
                FilterChip(selected = language == code, onClick = { language = code }, label = { Text(label) })
            }
        }

        Button(
            onClick = {
                val base = profile ?: UserProfile(userId = "demo_ravi", currentState = state)
                val updatedPersonal = (base.personal ?: PersonalDetails(fullName = name)).copy(fullName = name)
                onSave(base.copy(currentState = state, language = language, age = ageText.toIntOrNull(), personal = updatedPersonal))
            },
            modifier = Modifier.fillMaxWidth()
        ) { Text("Save & Continue", fontSize = 18.sp) }
    }
}

@Composable
fun ConsentScreen(
    profile: UserProfile?,
    onSaveConsents: (UserProfile) -> Unit,
    onConnectDigiLocker: () -> Unit
) {
    var sms by remember(profile) { mutableStateOf(profile?.consents?.sms ?: true) }
    var gmail by remember(profile) { mutableStateOf(profile?.consents?.gmail ?: false) }
    var digilocker by remember(profile) { mutableStateOf(profile?.consents?.digilocker ?: false) }

    val permLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { }

    LaunchedEffect(Unit) {
        val perms = buildList {
            add(Manifest.permission.RECEIVE_SMS)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                add(Manifest.permission.POST_NOTIFICATIONS)
            }
        }.toTypedArray()
        permLauncher.launch(perms)
    }

    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text("Permissions & Consent", style = MaterialTheme.typography.headlineSmall)

        ConsentRow("Government SMS Alerts", "Reads only verified government sender SMS to catch deadlines; OTPs are dropped immediately.", sms) { sms = it }
        ConsentRow("Gmail Notices (Simulated)", "Scans official .gov.in / .nic.in emails for renewal notices.", gmail) { gmail = it }
        ConsentRow("DigiLocker (Simulated)", "Imports document types and expiry dates without storing ID numbers.", digilocker) { digilocker = it }

        OutlinedButton(onClick = onConnectDigiLocker, modifier = Modifier.fillMaxWidth()) {
            Text("Connect DigiLocker Now")
        }

        Button(
            onClick = {
                val base = profile ?: UserProfile(userId = "demo_ravi", currentState = "karnataka")
                onSaveConsents(base.copy(consents = Consents(sms, gmail, digilocker)))
            },
            modifier = Modifier.fillMaxWidth()
        ) { Text("Save Consents", fontSize = 18.sp) }
    }
}

@Composable
fun ConsentRow(title: String, desc: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    Card(Modifier.fillMaxWidth()) {
        Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(title, fontWeight = FontWeight.Bold, fontSize = 17.sp)
                Text(desc, style = MaterialTheme.typography.bodyMedium)
            }
            Switch(checked = checked, onCheckedChange = onChange)
        }
    }
}

@Composable
fun HomeScreen(
    userId: String,
    profile: UserProfile?,
    repo: CivicRepository,
    onRefreshProfile: () -> Unit,
    onOpenNotification: (NotificationItem) -> Unit,
    onGoOnboarding: () -> Unit,
    onGoConsent: () -> Unit
) {
    var notifications by remember { mutableStateOf<List<NotificationItem>>(emptyList()) }
    var popupNotif by remember { mutableStateOf<NotificationItem?>(null) }

    // Poll unread notifications every 15s while Home is visible
    LaunchedEffect(userId, repo) {
        onRefreshProfile()
        while (true) {
            runCatching {
                val list = repo.getNotifications(userId, unreadOnly = true)
                notifications = list
                if (popupNotif == null) {
                    popupNotif = list.firstOrNull { it.type == "reminder" || it.type == "alert" }
                }
            }
            delay(15_000)
        }
    }

    popupNotif?.let { alert ->
        AlertDialog(
            onDismissRequest = { popupNotif = null },
            title = { Text(alert.title) },
            text = { Text(alert.body, fontSize = 16.sp) },
            confirmButton = {
                Button(onClick = {
                    popupNotif = null
                    onOpenNotification(alert)
                }) { Text("Open") }
            },
            dismissButton = {
                TextButton(onClick = { popupNotif = null }) { Text("Later") }
            }
        )
    }

    LazyColumn(
        Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Text(
                "Hello, ${profile?.personal?.fullName ?: userId}",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                TextButton(onClick = onGoOnboarding) { Text("Edit Profile") }
                TextButton(onClick = onGoConsent) { Text("Consents / DigiLocker") }
            }
        }

        item { Text("My Documents", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold) }

        val docs = profile?.documents.orEmpty()
        if (docs.isEmpty()) {
            item { Text("No documents linked yet. Connect DigiLocker in Consents.") }
        } else {
            items(docs) { doc ->
                DocumentCard(doc)
            }
        }

        item { Text("Notifications (${notifications.size})", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold) }

        items(notifications) { notif ->
            Card(onClick = { onOpenNotification(notif) }, modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(14.dp)) {
                    Text(notif.title, fontWeight = FontWeight.Bold, fontSize = 16.sp)
                    Text(notif.body)
                }
            }
        }
    }
}

@Composable
fun DocumentCard(doc: HeldDocument) {
    val statusText = remember(doc.expiryDate) {
        val exp = doc.expiryDate ?: return@remember "OK"
        runCatching {
            val days = ChronoUnit.DAYS.between(LocalDate.now(), LocalDate.parse(exp))
            when {
                days < 0 -> "Expired"
                days < 60 -> "Expiring Soon ($days d)"
                else -> "OK"
            }
        }.getOrDefault("OK")
    }

    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(doc.docId.uppercase().replace("_", " "), fontWeight = FontWeight.Bold, fontSize = 17.sp, modifier = Modifier.weight(1f))
                AssistChip(onClick = {}, label = { Text(statusText) })
            }
            Text("State: ${doc.issuedState ?: "Central"} | Expiry: ${doc.expiryDate ?: "No expiry"}")
            if (doc.origin == "digilocker") {
                Text("via DigiLocker (simulated)", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary)
            }
        }
    }
}

@Composable
fun AssistantScreen(
    userId: String,
    repo: CivicRepository,
    contextId: String?,
    bannerTitle: String?
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var input by remember { mutableStateOf("") }
    var loading by remember { mutableStateOf(false) }
    var messages by remember { mutableStateOf<List<Pair<Boolean, ChatResponse>>>(emptyList()) }

    // Auto-ask about the notification context if opened from a notification
    LaunchedEffect(contextId) {
        if (!contextId.isNullOrBlank() && messages.isEmpty()) {
            loading = true
            runCatching {
                val res = repo.sendChat(userId, "What should I do about this notice?", contextId)
                messages = messages + (false to res)
            }
            loading = false
        }
    }

    Column(Modifier.fillMaxSize().padding(12.dp)) {
        if (!bannerTitle.isNullOrBlank()) {
            Surface(color = MaterialTheme.colorScheme.secondaryContainer, modifier = Modifier.fillMaxWidth()) {
                Text("About: $bannerTitle", modifier = Modifier.padding(10.dp), fontWeight = FontWeight.SemiBold)
            }
            Spacer(Modifier.height(8.dp))
        }

        LazyColumn(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            items(messages) { (isUser, msg) ->
                if (isUser) {
                    Card(Modifier.fillMaxWidth()) {
                        Text("You: ${msg.reply}", modifier = Modifier.padding(12.dp), fontSize = 16.sp)
                    }
                } else {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Card(Modifier.fillMaxWidth()) {
                            Text(msg.reply, modifier = Modifier.padding(12.dp), fontSize = 16.sp)
                        }
                        msg.plan?.items?.forEach { item ->
                            ChecklistCard(item) { url ->
                                CustomTabsIntent.Builder().build().launchUrl(context, Uri.parse(url))
                            }
                        }
                    }
                }
            }
        }

        if (loading) LinearProgressIndicator(Modifier.fillMaxWidth())

        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(
                value = input,
                onValueChange = { input = it },
                placeholder = { Text("Ask e.g. Shifting from Bengaluru to Pune...") },
                modifier = Modifier.weight(1f)
            )
            IconButton(onClick = { /* Prompt C Voice hook */ }) {
                Icon(Icons.Default.Mic, contentDescription = "Voice")
            }
            Button(onClick = {
                val text = input.trim()
                if (text.isEmpty()) return@Button
                input = ""
                messages = messages + (true to ChatResponse(text, null, ""))
                scope.launch {
                    loading = true
                    runCatching {
                        val res = repo.sendChat(userId, text, contextId)
                        messages = messages + (false to res)
                    }.onFailure {
                        messages = messages + (false to ChatResponse("Could not reach backend: ${it.message}", null, ""))
                    }
                    loading = false
                }
            }) { Text("Send") }
        }
    }
}

@Composable
fun ChecklistCard(item: ChecklistItem, onOpenLink: (String) -> Unit) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(item.action, fontWeight = FontWeight.Bold, fontSize = 17.sp, modifier = Modifier.weight(1f))
                AssistChip(onClick = {}, label = { Text(item.priority.uppercase()) })
            }
            if (item.sources.isEmpty()) {
                Text("Unverified", color = Color(0xFFB00020), fontWeight = FontWeight.Bold)
            }
            Text(item.reason, fontSize = 15.sp)
            item.steps.forEachIndexed { idx, step ->
                Text("${idx + 1}. $step", fontSize = 15.sp)
            }
            Text("Fee: ${item.fee ?: "Check portal"}")
            item.officialLink?.let { link ->
                OutlinedButton(onClick = { onOpenLink(link) }) {
                    Text("Open official site")
                }
            }
        }
    }
}

@Composable
fun FormReviewScreen(formId: String, repo: CivicRepository, baseUrl: String) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var form by remember { mutableStateOf<PrefilledForm?>(null) }
    var confirmResult by remember { mutableStateOf<FormConfirmResponse?>(null) }

    LaunchedEffect(formId, repo) {
        runCatching { form = repo.getForm(formId) }
    }

    val currentForm = form
    if (currentForm == null) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text("Loading form...")
        }
        return
    }

    LazyColumn(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            Text("Review Form: ${currentForm.serviceId}", style = MaterialTheme.typography.headlineSmall)
            Text("We pre-fill what we know. You review and submit on the official portal.")
        }

        items(currentForm.fields.size) { index ->
            val field = currentForm.fields[index]
            val isMissing = field.needsUserInput || field.value.isNullOrBlank()
            Column(
                Modifier
                    .fillMaxWidth()
                    .background(if (isMissing) Color(0xFFFFF3E0) else Color.Transparent)
                    .padding(8.dp)
            ) {
                Text("${field.label}  ", fontWeight = FontWeight.SemiBold)
                OutlinedTextField(
                    value = field.value ?: "",
                    onValueChange = { newVal ->
                        val updatedFields = currentForm.fields.toMutableList()
                        updatedFields[index] = field.copy(value = newVal, needsUserInput = newVal.isBlank())
                        form = currentForm.copy(fields = updatedFields)
                    },
                    modifier = Modifier.fillMaxWidth(),
                    placeholder = { Text(if (isMissing) "Required — enter value" else "") }
                )
            }
        }

        item {
            Button(
                onClick = {
                    scope.launch {
                        runCatching {
                            val saved = repo.saveForm(currentForm)
                            confirmResult = repo.confirmForm(saved.formId)
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth()
            ) { Text("Confirm & Prepare Summary", fontSize = 18.sp) }
        }

        confirmResult?.let { res ->
            item {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(
                        onClick = {
                            val fullPdf = if (res.pdfUrl.startsWith("http")) res.pdfUrl else "$baseUrl${res.pdfUrl}"
                            CustomTabsIntent.Builder().build().launchUrl(context, Uri.parse(fullPdf))
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) { Text("Download summary PDF") }

                    Button(
                        onClick = {
                            CustomTabsIntent.Builder().build().launchUrl(context, Uri.parse(res.officialLink))
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) { Text("Open official site") }
                }
            }
        }
    }
}

@Composable
fun SettingsScreen(
    userId: String,
    baseUrl: String,
    useFake: Boolean,
    profile: UserProfile?,
    repo: CivicRepository,
    onUpdateSettings: (String, String, Boolean) -> Unit,
    onUpdateProfile: (UserProfile) -> Unit
) {
    val scope = rememberCoroutineScope()
    var urlInput by remember(baseUrl) { mutableStateOf(baseUrl) }
    var statusMsg by remember { mutableStateOf("") }

    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text("Settings", style = MaterialTheme.typography.headlineSmall)

        OutlinedTextField(
            value = urlInput,
            onValueChange = { urlInput = it },
            label = { Text("Backend URL (10.0.2.2:8000 or laptop LAN IP)") },
            modifier = Modifier.fillMaxWidth()
        )
        Button(onClick = { onUpdateSettings(userId, urlInput, useFake); statusMsg = "URL saved" }) {
            Text("Save Backend URL")
        }

        Text("Demo User", fontWeight = FontWeight.Bold)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf("demo_ravi", "demo_ajji").forEach { id ->
                FilterChip(
                    selected = userId == id,
                    onClick = { onUpdateSettings(id, urlInput, useFake) },
                    label = { Text(id) }
                )
            }
        }

        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("Offline Fake Data Mode", modifier = Modifier.weight(1f))
            Switch(checked = useFake, onCheckedChange = { onUpdateSettings(userId, urlInput, it) })
        }

        profile?.let { p ->
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("SMS Monitoring Consent", modifier = Modifier.weight(1f))
                Switch(
                    checked = p.consents.sms,
                    onCheckedChange = { onUpdateProfile(p.copy(consents = p.consents.copy(sms = it))) }
                )
            }
        }

        Button(
            onClick = {
                scope.launch {
                    runCatching {
                        repo.simulateSms(userId, 0)
                        statusMsg = "Simulated government SMS sent! Check Home notifications."
                    }.onFailure { statusMsg = "Failed: ${it.message}" }
                }
            },
            modifier = Modifier.fillMaxWidth()
        ) { Text("Simulate government SMS") }

        if (statusMsg.isNotEmpty()) Text(statusMsg, color = MaterialTheme.colorScheme.primary)
    }
}