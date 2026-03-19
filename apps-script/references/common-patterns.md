# Apps Script Common Patterns

## Read-Process-Write (Spreadsheet)

The fundamental pattern for any Sheets automation:

```javascript
function processSheet() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var data = sheet.getDataRange().getValues(); // 2D array, all data

  for (var i = 1; i < data.length; i++) { // Skip header row (index 0)
    data[i][3] = data[i][1] * data[i][2]; // Col D = Col B * Col C
  }

  sheet.getDataRange().setValues(data); // Write all at once
}
```

## Custom Menu

```javascript
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('My Tools')
    .addItem('Run Report', 'generateReport')
    .addSeparator()
    .addSubMenu(
      SpreadsheetApp.getUi().createMenu('Advanced')
        .addItem('Reset Data', 'resetData')
    )
    .addToUi();
}
```

Works in Sheets, Docs, Slides, and Forms (container-bound only).

## HTML Sidebar / Dialog

### Server side (Code.gs)
```javascript
function showSidebar() {
  var html = HtmlService.createHtmlOutputFromFile('Sidebar')
    .setTitle('My Sidebar');
  SpreadsheetApp.getUi().showSidebar(html);
}

function showDialog() {
  var html = HtmlService.createHtmlOutputFromFile('Dialog')
    .setWidth(400)
    .setHeight(300);
  SpreadsheetApp.getUi().showModalDialog(html, 'My Dialog');
}

// Called from client-side JS
function getSheetData() {
  return SpreadsheetApp.getActiveSpreadsheet().getActiveSheet()
    .getDataRange().getValues();
}
```

### Client side (Sidebar.html)
```html
<!DOCTYPE html>
<html>
<head>
  <base target="_top">
  <style>
    body { font-family: Arial, sans-serif; padding: 10px; }
    button { margin: 5px 0; }
  </style>
</head>
<body>
  <h3>My Sidebar</h3>
  <button onclick="loadData()">Load Data</button>
  <div id="output"></div>

  <script>
    function loadData() {
      google.script.run
        .withSuccessHandler(function(data) {
          document.getElementById('output').innerText = JSON.stringify(data);
        })
        .withFailureHandler(function(err) {
          document.getElementById('output').innerText = 'Error: ' + err.message;
        })
        .getSheetData();
    }
  </script>
</body>
</html>
```

**Key points:**
- `google.script.run` calls server functions asynchronously
- Always use `.withSuccessHandler()` and `.withFailureHandler()`
- Return values must be serializable (no Date objects, no functions)
- `google.script.host.close()` closes the sidebar/dialog

## Continuation Pattern (Long Tasks)

For tasks that exceed the 6-minute limit. See also `references/performance.md`.

```javascript
function startProcess() {
  PropertiesService.getScriptProperties().setProperty('lastRow', '0');
  ScriptApp.newTrigger('continueProcess')
    .timeBased().everyMinutes(1).create();
  continueProcess(); // Run first chunk immediately
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
    // Done — clean up trigger
    ScriptApp.getProjectTriggers().forEach(function(t) {
      if (t.getHandlerFunction() === 'continueProcess') {
        ScriptApp.deleteTrigger(t);
      }
    });
    props.deleteProperty('lastRow');
    Logger.log('Processing complete');
  } else {
    props.setProperty('lastRow', limit.toString());
  }
}
```

## UrlFetchApp with Retry and Backoff

```javascript
function fetchWithRetry(url, options, maxRetries) {
  maxRetries = maxRetries || 3;
  options = options || {};
  options.muteHttpExceptions = true;

  for (var attempt = 0; attempt < maxRetries; attempt++) {
    try {
      var response = UrlFetchApp.fetch(url, options);
      var code = response.getResponseCode();

      if (code >= 200 && code < 300) return response;
      if (code >= 400 && code < 500) return response; // Client error — don't retry

      // 5xx — server error, retry with backoff
      Utilities.sleep(Math.pow(2, attempt) * 1000);
    } catch (e) {
      if (attempt === maxRetries - 1) throw e;
      Utilities.sleep(Math.pow(2, attempt) * 1000);
    }
  }
  throw new Error('Max retries exceeded for ' + url);
}
```

## Webhook Receiver (Web App)

```javascript
function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);

    // Log to spreadsheet
    var sheet = SpreadsheetApp.openById('SHEET_ID').getSheetByName('Webhooks');
    sheet.appendRow([new Date(), JSON.stringify(data), data.event]);

    return ContentService.createTextOutput(
      JSON.stringify({ status: 'ok' })
    ).setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    console.error('Webhook error: ' + err.message);
    return ContentService.createTextOutput(
      JSON.stringify({ status: 'error', message: err.message })
    ).setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  // Health check
  return ContentService.createTextOutput(
    JSON.stringify({ status: 'healthy', timestamp: new Date().toISOString() })
  ).setMimeType(ContentService.MimeType.JSON);
}
```

## Email with Template

```javascript
function sendTemplatedEmail(recipient, name, data) {
  var template = HtmlService.createTemplateFromFile('EmailTemplate');
  template.name = name;
  template.data = data;
  var htmlBody = template.evaluate().getContent();

  GmailApp.sendEmail(recipient, 'Your Report', '', {
    htmlBody: htmlBody,
    name: 'My App'
  });
}
```

**EmailTemplate.html:**
```html
<h2>Hello <?= name ?>,</h2>
<p>Here's your report:</p>
<table>
  <? for (var i = 0; i < data.length; i++) { ?>
    <tr><td><?= data[i][0] ?></td><td><?= data[i][1] ?></td></tr>
  <? } ?>
</table>
```

## Sheet-to-JSON API

Expose sheet data as a JSON API:

```javascript
function doGet(e) {
  var sheetName = e.parameter.sheet || 'Sheet1';
  var sheet = SpreadsheetApp.openById('SHEET_ID').getSheetByName(sheetName);

  if (!sheet) {
    return ContentService.createTextOutput(
      JSON.stringify({ error: 'Sheet not found' })
    ).setMimeType(ContentService.MimeType.JSON);
  }

  var data = sheet.getDataRange().getValues();
  var headers = data[0];
  var rows = data.slice(1).map(function(row) {
    var obj = {};
    headers.forEach(function(h, i) { obj[h] = row[i]; });
    return obj;
  });

  return ContentService.createTextOutput(
    JSON.stringify({ data: rows, count: rows.length })
  ).setMimeType(ContentService.MimeType.JSON);
}
```

## Form Response Processing

```javascript
function onFormSubmit(e) {
  var responses = e.namedValues; // { "Name": ["John"], "Email": ["john@example.com"] }
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Processed');

  // Validate
  var email = responses['Email'][0];
  if (!email || !email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
    console.warn('Invalid email: ' + email);
    return;
  }

  // Process and record
  sheet.appendRow([
    new Date(),
    responses['Name'][0],
    email,
    'Processed'
  ]);

  // Send confirmation
  MailApp.sendEmail(email, 'Thanks for submitting!',
    'Hi ' + responses['Name'][0] + ', we received your response.');
}
```

**Note:** This must be an installable trigger (not simple) because it calls `MailApp`.
