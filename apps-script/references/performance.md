# Apps Script Performance Reference

## Batch Reads/Writes (Critical)

The single most important optimization. Cell-by-cell operations are ~70x slower than batch.

```javascript
// BAD — 10,000 individual service calls (~70 seconds)
for (var i = 1; i <= 100; i++) {
  for (var j = 1; j <= 100; j++) {
    sheet.getRange(i, j).setValue(data[i][j]);
  }
}

// GOOD — 1 read + 1 write (~1 second)
var data = sheet.getRange(1, 1, 100, 100).getValues();
// ... process data array in pure JS ...
sheet.getRange(1, 1, 100, 100).setValues(data);
```

**Rules:**
- Read entire ranges with `getValues()` / `getDataRange().getValues()`
- Process data as 2D JS arrays in memory
- Write back with `setValues()` in a single call
- Never alternate reads and writes — batch all reads first, then all writes
- Use `getDataRange()` when you need all data (auto-sizes to content)

## Minimize Service Calls

Every call to a Google service (SpreadsheetApp, DriveApp, etc.) is a remote procedure call with network latency.

```javascript
// BAD — getRange called in loop
for (var i = 1; i <= rows; i++) {
  var name = sheet.getRange(i, 1).getValue();
  var email = sheet.getRange(i, 2).getValue();
  sendEmail(name, email);
}

// GOOD — one service call, loop in JS
var data = sheet.getRange(1, 1, rows, 2).getValues();
for (var i = 0; i < data.length; i++) {
  sendEmail(data[i][0], data[i][1]);
}
```

## CacheService

Cache expensive external API responses. Three scopes available.

```javascript
function getExternalData() {
  var cache = CacheService.getScriptCache();
  var cached = cache.get("api-response");
  if (cached != null) return JSON.parse(cached);

  var response = UrlFetchApp.fetch("https://api.example.com/data");
  var data = response.getContentText();
  cache.put("api-response", data, 1500); // TTL in seconds (max 21600 = 6hr)
  return JSON.parse(data);
}
```

| Scope | Method | Shared With |
|-------|--------|------------|
| Script | `getScriptCache()` | All users of the script |
| User | `getUserCache()` | Only the current user |
| Document | `getDocumentCache()` | All users of the document |

**Limits:** 100 KB max per entry, 500 entries per cache store.

## Parallel HTTP with fetchAll

```javascript
// BAD — sequential fetches
urls.forEach(function(url) {
  UrlFetchApp.fetch(url); // Waits for each
});

// GOOD — parallel fetches
var requests = urls.map(function(url) {
  return { url: url, muteHttpExceptions: true };
});
var responses = UrlFetchApp.fetchAll(requests); // All at once
```

## Libraries Add Latency

Each function call to an Apps Script library is a remote invocation. In UI-heavy contexts (custom functions, sidebars, add-ons), this latency compounds.

**Recommendation:** For performance-critical code, copy library functions into the project instead of importing the library.

## Timeout Handling — Continuation Pattern

Scripts have a 6-minute hard limit. For large datasets, split into chunks and resume via time-driven trigger.

```javascript
function startProcess() {
  PropertiesService.getScriptProperties().setProperty('lastRow', '0');
  ScriptApp.newTrigger('continueProcess')
    .timeBased().everyMinutes(1).create();
}

function continueProcess() {
  var props = PropertiesService.getScriptProperties();
  var lastRow = parseInt(props.getProperty('lastRow'));
  var sheet = SpreadsheetApp.openById('SHEET_ID').getActiveSheet();
  var data = sheet.getDataRange().getValues();
  var limit = Math.min(lastRow + 500, data.length);

  for (var i = lastRow; i < limit; i++) {
    // Process row i
  }

  if (limit >= data.length) {
    // Done — clean up
    ScriptApp.getProjectTriggers().forEach(function(t) {
      if (t.getHandlerFunction() === 'continueProcess') {
        ScriptApp.deleteTrigger(t);
      }
    });
    props.deleteProperty('lastRow');
  } else {
    props.setProperty('lastRow', limit.toString());
  }
}
```

**Alternative — Time check within a single execution:**
```javascript
function processWithTimeCheck() {
  var startTime = new Date().getTime();
  var MAX_RUNTIME = 5 * 60 * 1000; // 5 min (leave 1 min buffer)
  var data = sheet.getDataRange().getValues();
  var props = PropertiesService.getScriptProperties();
  var i = parseInt(props.getProperty('lastRow') || '0');

  for (; i < data.length; i++) {
    // Process row i
    if (new Date().getTime() - startTime > MAX_RUNTIME) {
      props.setProperty('lastRow', i.toString());
      return; // Trigger will resume
    }
  }
  props.deleteProperty('lastRow');
}
```

## SpreadsheetApp.flush()

Forces pending changes to be written immediately. Useful when you need intermediate results visible before continuing, but adds latency — use sparingly.

```javascript
sheet.getRange("A1").setValue("Processing...");
SpreadsheetApp.flush(); // Force the UI to update
// ... long operation ...
sheet.getRange("A1").setValue("Done!");
```
