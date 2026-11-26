# CivicSaathi backend API

The backend listens on port `8000`. Use the backend base URL configured
for the Android app. `/docs` shows the registered endpoints, and
`/openapi.json` provides their schemas.

## Relocation chat

`POST /chat`

```json
{
  "user_id": "demo_ravi",
  "message": "My family is shifting from Bengaluru to Pune."
}
```

The response includes `reply`, `plan`, and `conversation_id`.
`plan` can be null. In the relocation demo, `plan.items` starts with
Aadhaar. Use the conversation ID with `GET /trace/{conversation_id}/view`.

## SMS notification to chat

Send the demo SMS with `POST /demo/simulate-sms`.

```json
{
  "user_id": "demo_ravi",
  "sample_index": 0
}
```

Index `0` is Ravi's licence SMS when the shared fallback samples are in use.
The endpoint returns HTTP 202 and a `message_id`. Poll
`GET /notifications/demo_ravi` for the new reminder. When the user taps it,
send its `context_id` in the chat request.

```json
{
  "user_id": "demo_ravi",
  "message": "What is this reminder about?",
  "context_id": "MESSAGE_ID_FROM_NOTIFICATION"
}
```

## Voter-shift draft

For a notification with `open_target` set to `form`, use its `context_id`
as the form ID. Open it with `GET /forms/{form_id}`. Confirm review with
`POST /forms/{form_id}/confirm`. The response contains `pdf_url` and
`official_link`. Resolve the relative `pdf_url` against the backend base URL.
The user submits the form themselves on the official portal.

## Simulated DigiLocker

Send `{"user_id":"demo_ravi"}` to `POST /connect/digilocker/start`.
Open the returned `url` to show the consent page. After the callback,
refresh `GET /profile/demo_ravi` to show the imported documents.
## Android integration

| Endpoint | Request and response |
|---|---|
| `PUT /profile/{user_id}` | Send a full `UserProfile` with the same `user_id`. Returns the saved profile. |
| `GET /notifications/{user_id}?unread=true` | Returns unread notifications. Omit `unread` for all notifications. |
| `POST /notifications/{notification_id}/read` | No request body. Returns the notification with `read: true`. |
| `PUT /forms/{form_id}` | Send the edited `PrefilledForm`. Returns the saved draft. Sensitive ID fields are completed on the official portal. |
| `POST /devices` | Send `{"user_id":"demo_ravi","fcm_token":"demo-token"}`. Returns `{"device_id":"..."}`. |
| `GET /connect/digilocker/start?user_id=demo_ravi` | Returns the simulated consent URL. The demo callback uses `demo_ravi` and `demo_request`. |
| `GET /connect/gmail/start?user_id=demo_ravi` | Returns `{"simulated":true}` and saves simulated Gmail consent. |
| `POST /connect/{source}/revoke` | Send `{"user_id":"demo_ravi"}`. Returns `{"revoked":true}`. |