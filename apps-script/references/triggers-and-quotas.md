# Apps Script Triggers & Quotas Reference

## Simple Triggers

Reserved function names that run automatically. No setup needed.

| Trigger | Fires When | Available In |
|---------|-----------|--------------|
| `onOpen(e)` | User opens file (with edit access) | Sheets, Docs, Slides, Forms |
| `onEdit(e)` | User edits a cell value | Sheets only |
| `onInstall(e)` | User installs an Editor add-on | Add-ons |
| `onSelectionChange(e)` | User changes selection | Sheets only |
| `doGet(e)` | HTTP GET to web app | Web apps |
| `doPost(e)` | HTTP POST to web app | Web apps |

### Restrictions (Critical)

- **Cannot call authorized services** — no Gmail, Drive, UrlFetch, Calendar, etc.
- Cannot access other files (only the bound container)
- Cannot open URLs or show authorization dialogs
- **30-second max** execution time
- Don't fire from script executions or API requests
- Don't fire in read-only mode
- Must be in a container-bound script (except add-ons)

### Common Mistake
```javascript
// This SILENTLY FAILS in a simple onEdit trigger:
function onEdit(e) {
  UrlFetchApp.fetch("https://webhook.example.com/notify"); // UNAUTHORIZED
}

// Fix: use an installable trigger instead
```

## Installable Triggers

Created via UI or programmatically. Run under the **creator's** account.

| Type | Description |
|------|-------------|
| Open | Fires when document opens (CAN call authorized services) |
| Edit | Fires when spreadsheet is edited |
| Change | Fires on structural changes (insert row, add sheet) — Sheets only |
| Form Submit | Fires when a form response is submitted |
| Time-driven | Fires on a schedule |

### Creating Triggers Programmatically

```javascript
// Time-driven: every 6 hours
ScriptApp.newTrigger("myFunction")
  .timeBased()
  .everyHours(6)
  .create();

// Time-driven: every Monday at 9 AM
ScriptApp.newTrigger("myFunction")
  .timeBased()
  .onWeekDay(ScriptApp.WeekDay.MONDAY)
  .atHour(9)
  .create();

// Spreadsheet onEdit (installable — CAN call authorized services)
ScriptApp.newTrigger("onEditHandler")
  .forSpreadsheet(SpreadsheetApp.getActive())
  .onEdit()
  .create();

// Form submit
ScriptApp.newTrigger("onFormSubmitHandler")
  .forForm(FormApp.getActiveForm())
  .onFormSubmit()
  .create();
```

### Deleting Triggers
```javascript
ScriptApp.getProjectTriggers().forEach(function(t) {
  if (t.getHandlerFunction() === 'myFunction') {
    ScriptApp.deleteTrigger(t);
  }
});
```

### Key Characteristics
- Run under the **creator's** account (not the triggering user)
- Can call any authorized service the creator has granted
- Persist across sessions
- **Max 20 triggers per user per script**
- Don't fire from programmatic changes (prevents infinite loops... mostly)

### Infinite Loop Prevention
An installable `onEdit` trigger that writes to the sheet will NOT re-trigger itself (installable triggers don't fire from programmatic edits). But be careful with `onChange` triggers and `Form.submitGrades()`.

---

## Runtime Limits (Per Execution)

| Feature | Limit |
|---------|-------|
| Script runtime | **6 minutes** |
| Custom function runtime | **30 seconds** |
| Workspace add-on action runtime | **30 seconds** |
| Simple trigger runtime | **30 seconds** |
| Simultaneous executions per user | 30 |
| Simultaneous executions per script | 1,000 |

## Daily Quotas (Per User, Resets 24h After First Request)

| Feature | Consumer (free) | Google Workspace |
|---------|----------------|-----------------|
| Email recipients | 100/day | 1,500/day |
| Calendar events created | 5,000/day | 10,000/day |
| Documents created | 250/day | 1,500/day |
| Spreadsheets created | 250/day | 1,500/day |
| Drive files created | 250/day | — |
| URL Fetch calls | **20,000/day** | **100,000/day** |
| Script total runtime (triggers) | **90 min/day** | **6 hr/day** |
| Properties read/write | 50,000/day | 500,000/day |

## Per-Call Limits

| Feature | Limit |
|---------|-------|
| Email recipients per message | 50 |
| Email body size | 200 KB (consumer) / 400 KB (Workspace) |
| Email attachments | 250/message, 25 MB total |
| URL Fetch response size | 50 MB |
| URL Fetch headers | 100/call, 8 KB/header |
| Properties value size | **9 KB per value** |
| Properties total storage | **500 KB per property store** |
| Triggers per user per script | **20** |
| Cache entry size | 100 KB |
| Cache entries per store | 500 |

## Monitoring Quotas

```javascript
// Check remaining email quota
var remaining = MailApp.getRemainingDailyQuota();
Logger.log("Emails remaining today: " + remaining);
```

- **Apps Script Dashboard** > My Executions — execution history, status, durations
- **Google Cloud Console** — service-specific quotas (requires standard GCP project)
