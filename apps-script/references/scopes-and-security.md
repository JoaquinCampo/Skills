# Apps Script OAuth Scopes & Security Reference

## OAuth Scopes

### How Scopes Work
- Apps Script auto-detects scopes by scanning code for service calls
- Listed in `appsscript.json` under `oauthScopes`
- Users see a consent screen listing permissions on first run
- **For published apps, always set explicit scopes** (don't rely on auto-detection)

### Setting Explicit Scopes
```json
{
  "timeZone": "America/New_York",
  "dependencies": {},
  "oauthScopes": [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/script.send_mail"
  ]
}
```

### Scope Narrowing — Always Use the Most Restrictive

| Instead of | Use | When |
|-----------|-----|------|
| `auth/spreadsheets` | `auth/spreadsheets.readonly` | Only reading spreadsheet data |
| `auth/spreadsheets` | `auth/spreadsheets.currentonly` | Only accessing the bound spreadsheet |
| `auth/drive` | `auth/drive.file` | Only accessing files the app created/opened |
| `auth/drive` | `auth/drive.readonly` | Only reading files |
| `auth/gmail` | `auth/gmail.readonly` | Only reading email |
| `auth/gmail` | `auth/gmail.send` | Only sending email |
| `auth/gmail` | `auth/script.send_mail` | Simple sends via MailApp (not GmailApp) |
| `auth/calendar` | `auth/calendar.readonly` | Only reading calendar events |

### Scope Categories & Verification

| Category | Examples | Verification Required |
|----------|---------|----------------------|
| Non-sensitive | `openid`, `profile`, `email` | None |
| Sensitive | Read/write email, calendar, contacts | OAuth verification for public apps |
| Restricted | Full Gmail (`mail.google.com`), full Drive (`auth/drive`) | Security assessment + annual audit |

### Handling Granular Permissions
Users can deny individual scopes. Handle partial authorization:
```javascript
ScriptApp.requireScopes(ScriptApp.AuthMode.FULL, [
  'https://mail.google.com/',
  'https://www.googleapis.com/auth/spreadsheets'
]);
// Execution halts and prompts if scopes not yet granted
```

---

## Secret Management

### Never Hardcode Secrets
```javascript
// BAD
var API_KEY = "sk-abc123secret";

// GOOD
var API_KEY = PropertiesService.getScriptProperties().getProperty('API_KEY');
```

### Setting Properties
**Via script (one-time setup):**
```javascript
PropertiesService.getScriptProperties().setProperties({
  'API_KEY': 'sk-abc123...',
  'WEBHOOK_URL': 'https://hooks.slack.com/...'
});
```
**Via UI:** Apps Script editor > Project Settings > Script Properties

### PropertiesService Scopes

| Store | Method | Scope | Shared With |
|-------|--------|-------|-------------|
| Script | `getScriptProperties()` | Per project | All users of the script |
| User | `getUserProperties()` | Per user per project | Only the current user |
| Document | `getDocumentProperties()` | Per document (bound only) | All users of the document |

**Limits:** 9 KB per value, 500 KB per property store.

---

## Input Validation

### Web App Input (`doGet`/`doPost`)
```javascript
function doPost(e) {
  // Validate content type
  if (e.postData.type !== 'application/json') {
    return ContentService.createTextOutput(
      JSON.stringify({ error: 'Expected JSON' })
    ).setMimeType(ContentService.MimeType.JSON);
  }

  // Parse and validate
  var body;
  try {
    body = JSON.parse(e.postData.contents);
  } catch (err) {
    return ContentService.createTextOutput(
      JSON.stringify({ error: 'Invalid JSON' })
    ).setMimeType(ContentService.MimeType.JSON);
  }

  // Validate required fields
  if (!body.name || typeof body.name !== 'string' || body.name.length > 200) {
    return ContentService.createTextOutput(
      JSON.stringify({ error: 'Invalid name' })
    ).setMimeType(ContentService.MimeType.JSON);
  }

  // Process...
}
```

### Spreadsheet Input (onEdit)
```javascript
function onEditHandler(e) {
  var value = e.value;
  if (typeof value !== 'string' || value.length > 1000) {
    e.range.setValue(''); // Reject
    return;
  }
  // Sanitize before using in HTML output
  var safe = value.replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
```

---

## Web App Security

- **Prevent clickjacking:**
  ```javascript
  HtmlService.createHtmlOutput(html)
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.DENY);
  ```
- **Verify user identity** when executing as "User accessing the web app":
  ```javascript
  var userEmail = Session.getActiveUser().getEmail();
  ```
- **Set correct Content-Type** for API responses:
  ```javascript
  ContentService.createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
  ```
- **Don't reflect user input unsanitized** in `ContentService.createTextOutput()`

---

## Concurrency Safety

Use `LockService` when multiple users or triggers may write to the same resource:

```javascript
function updateSharedCounter() {
  var lock = LockService.getScriptLock();
  try {
    lock.waitLock(10000); // Wait up to 10 seconds
    var props = PropertiesService.getScriptProperties();
    var count = parseInt(props.getProperty('count') || '0');
    props.setProperty('count', (count + 1).toString());
  } catch (e) {
    console.error('Could not obtain lock: ' + e.message);
  } finally {
    lock.releaseLock();
  }
}
```

Three lock scopes: `getScriptLock()` (all users), `getUserLock()` (per user), `getDocumentLock()` (per document).

---

## Security Checklist

Before deploying any Apps Script project:

- [ ] No hardcoded secrets in source files
- [ ] Scopes in `appsscript.json` are the narrowest possible
- [ ] All `doGet`/`doPost` input is validated and sanitized
- [ ] No `eval()` or dynamic code construction from user input
- [ ] `LockService` used for concurrent writes to shared state
- [ ] Web app access level is appropriate ("Anyone" only if truly public)
- [ ] Installable triggers are reviewed (they run as creator, not user)
- [ ] HTML output uses XFrameOptions DENY where appropriate
