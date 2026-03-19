# Apps Script Accountancy Patterns for Google Sheets

## Currency & Number Formatting

```javascript
// Format a range as currency
function formatAsCurrency(sheet, range, currencySymbol) {
  currencySymbol = currencySymbol || '$';
  sheet.getRange(range).setNumberFormat(currencySymbol + '#,##0.00');
}

// Format negative numbers in red with parentheses (accounting style)
function setAccountingFormat(sheet, range) {
  sheet.getRange(range).setNumberFormat('$#,##0.00;($#,##0.00)');
}

// Format as percentage
function setPercentFormat(sheet, range) {
  sheet.getRange(range).setNumberFormat('0.00%');
}
```

## Journal Entry Automation

```javascript
/**
 * Append a double-entry journal entry to the Journal sheet.
 * Validates that debits === credits before writing.
 */
function postJournalEntry(date, description, lines) {
  // lines = [{ account: "1000 - Cash", debit: 500, credit: 0 }, ...]
  var totalDebit = 0, totalCredit = 0;
  lines.forEach(function(line) {
    totalDebit += (line.debit || 0);
    totalCredit += (line.credit || 0);
  });

  // Validate double-entry balance
  if (Math.abs(totalDebit - totalCredit) > 0.005) {
    throw new Error('Entry does not balance: debits=' + totalDebit.toFixed(2) +
                     ' credits=' + totalCredit.toFixed(2));
  }

  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Journal');
  var entryId = Utilities.getUuid().substring(0, 8);

  lines.forEach(function(line) {
    sheet.appendRow([
      date,
      entryId,
      description,
      line.account,
      line.debit || '',
      line.credit || ''
    ]);
  });

  return entryId;
}
```

## Chart of Accounts Lookup

```javascript
/**
 * Build a lookup map from the Chart of Accounts sheet.
 * Returns { "1000": { name: "Cash", type: "Asset", ... }, ... }
 */
function getChartOfAccounts() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Chart of Accounts');
  var data = sheet.getDataRange().getValues();
  var headers = data[0];
  var accounts = {};

  for (var i = 1; i < data.length; i++) {
    var code = String(data[i][0]);
    accounts[code] = {
      name: data[i][1],
      type: data[i][2],       // Asset, Liability, Equity, Revenue, Expense
      subtype: data[i][3],
      active: data[i][4] !== false
    };
  }
  return accounts;
}

/**
 * Custom function: look up account name by code.
 * Usage in cell: =ACCOUNT_NAME("1000")
 */
function ACCOUNT_NAME(code) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Chart of Accounts');
  var data = sheet.getDataRange().getValues();
  for (var i = 1; i < data.length; i++) {
    if (String(data[i][0]) === String(code)) return data[i][1];
  }
  return 'Unknown';
}
```

## Bank Reconciliation

```javascript
/**
 * Compare bank statement rows against ledger entries.
 * Marks matched rows in both sheets.
 */
function reconcileBank() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var bankSheet = ss.getSheetByName('Bank Statement');
  var ledgerSheet = ss.getSheetByName('Ledger');

  var bankData = bankSheet.getDataRange().getValues();
  var ledgerData = ledgerSheet.getDataRange().getValues();

  // Build index of ledger entries by amount (for quick matching)
  // ledgerData columns: [Date, Description, Amount, Reconciled]
  var ledgerByAmount = {};
  for (var i = 1; i < ledgerData.length; i++) {
    if (ledgerData[i][3] === true) continue; // Already reconciled
    var amt = parseFloat(ledgerData[i][2]).toFixed(2);
    if (!ledgerByAmount[amt]) ledgerByAmount[amt] = [];
    ledgerByAmount[amt].push(i);
  }

  var matched = 0;
  // bankData columns: [Date, Description, Amount, Reconciled]
  for (var b = 1; b < bankData.length; b++) {
    if (bankData[b][3] === true) continue; // Already reconciled
    var bankAmt = parseFloat(bankData[b][2]).toFixed(2);
    var candidates = ledgerByAmount[bankAmt];

    if (candidates && candidates.length > 0) {
      var ledgerRow = candidates.shift(); // Match first candidate

      // Mark both as reconciled
      bankData[b][3] = true;
      ledgerData[ledgerRow][3] = true;
      matched++;
    }
  }

  // Write back
  bankSheet.getDataRange().setValues(bankData);
  ledgerSheet.getDataRange().setValues(ledgerData);

  SpreadsheetApp.getUi().alert(
    'Reconciliation complete: ' + matched + ' transactions matched.'
  );
}
```

## Accounts Receivable Aging Report

```javascript
/**
 * Generate an AR aging report from an Invoices sheet.
 * Invoices columns: [Invoice#, Customer, Date, DueDate, Amount, PaidDate]
 */
function generateAgingReport() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var invoices = ss.getSheetByName('Invoices').getDataRange().getValues();
  var today = new Date();

  var aging = {}; // { customer: { current: 0, d30: 0, d60: 0, d90: 0, over90: 0 } }

  for (var i = 1; i < invoices.length; i++) {
    var customer = invoices[i][1];
    var dueDate = new Date(invoices[i][3]);
    var amount = parseFloat(invoices[i][4]);
    var paidDate = invoices[i][5];

    if (paidDate) continue; // Already paid

    if (!aging[customer]) {
      aging[customer] = { current: 0, d30: 0, d60: 0, d90: 0, over90: 0, total: 0 };
    }

    var daysOverdue = Math.floor((today - dueDate) / (1000 * 60 * 60 * 24));

    if (daysOverdue <= 0) aging[customer].current += amount;
    else if (daysOverdue <= 30) aging[customer].d30 += amount;
    else if (daysOverdue <= 60) aging[customer].d60 += amount;
    else if (daysOverdue <= 90) aging[customer].d90 += amount;
    else aging[customer].over90 += amount;

    aging[customer].total += amount;
  }

  // Write report
  var report = ss.getSheetByName('Aging Report');
  if (!report) report = ss.insertSheet('Aging Report');
  report.clear();

  report.appendRow(['Customer', 'Current', '1-30 Days', '31-60 Days', '61-90 Days', '90+ Days', 'Total']);
  var grandTotal = { current: 0, d30: 0, d60: 0, d90: 0, over90: 0, total: 0 };

  Object.keys(aging).sort().forEach(function(customer) {
    var a = aging[customer];
    report.appendRow([customer, a.current, a.d30, a.d60, a.d90, a.over90, a.total]);
    grandTotal.current += a.current;
    grandTotal.d30 += a.d30;
    grandTotal.d60 += a.d60;
    grandTotal.d90 += a.d90;
    grandTotal.over90 += a.over90;
    grandTotal.total += a.total;
  });

  report.appendRow(['TOTAL', grandTotal.current, grandTotal.d30, grandTotal.d60,
                     grandTotal.d90, grandTotal.over90, grandTotal.total]);

  // Format
  var lastRow = report.getLastRow();
  var dataRange = report.getRange(2, 2, lastRow - 1, 6);
  dataRange.setNumberFormat('$#,##0.00;($#,##0.00)');
  report.getRange(1, 1, 1, 7).setFontWeight('bold');
  report.getRange(lastRow, 1, 1, 7).setFontWeight('bold');
  report.autoResizeColumns(1, 7);
}
```

## Trial Balance Generator

```javascript
/**
 * Generate trial balance from the Journal sheet.
 * Journal columns: [Date, EntryID, Description, Account, Debit, Credit]
 */
function generateTrialBalance() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var journal = ss.getSheetByName('Journal').getDataRange().getValues();

  var balances = {}; // { "1000 - Cash": { debit: 0, credit: 0 } }

  for (var i = 1; i < journal.length; i++) {
    var account = journal[i][3];
    var debit = parseFloat(journal[i][4]) || 0;
    var credit = parseFloat(journal[i][5]) || 0;

    if (!balances[account]) balances[account] = { debit: 0, credit: 0 };
    balances[account].debit += debit;
    balances[account].credit += credit;
  }

  var report = ss.getSheetByName('Trial Balance');
  if (!report) report = ss.insertSheet('Trial Balance');
  report.clear();

  report.appendRow(['Account', 'Debit', 'Credit']);
  var totalDebit = 0, totalCredit = 0;

  Object.keys(balances).sort().forEach(function(account) {
    var b = balances[account];
    report.appendRow([account, b.debit, b.credit]);
    totalDebit += b.debit;
    totalCredit += b.credit;
  });

  report.appendRow(['TOTAL', totalDebit, totalCredit]);

  // Format and validate
  var lastRow = report.getLastRow();
  report.getRange(2, 2, lastRow - 1, 2).setNumberFormat('$#,##0.00;($#,##0.00)');
  report.getRange(1, 1, 1, 3).setFontWeight('bold');
  report.getRange(lastRow, 1, 1, 3).setFontWeight('bold');
  report.autoResizeColumns(1, 3);

  if (Math.abs(totalDebit - totalCredit) > 0.005) {
    SpreadsheetApp.getUi().alert(
      'WARNING: Trial balance does not balance!\n' +
      'Debits: $' + totalDebit.toFixed(2) + '\n' +
      'Credits: $' + totalCredit.toFixed(2) + '\n' +
      'Difference: $' + Math.abs(totalDebit - totalCredit).toFixed(2)
    );
  }
}
```

## Period Close Checklist Menu

```javascript
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Accounting')
    .addItem('Post Journal Entry...', 'showJournalEntryDialog')
    .addItem('Reconcile Bank', 'reconcileBank')
    .addSeparator()
    .addSubMenu(SpreadsheetApp.getUi().createMenu('Reports')
      .addItem('Trial Balance', 'generateTrialBalance')
      .addItem('AR Aging Report', 'generateAgingReport')
      .addItem('P&L Summary', 'generatePnL')
      .addItem('Balance Sheet', 'generateBalanceSheet'))
    .addSeparator()
    .addSubMenu(SpreadsheetApp.getUi().createMenu('Period Close')
      .addItem('Run Close Checklist', 'runCloseChecklist')
      .addItem('Lock Period', 'lockPeriod'))
    .addToUi();
}
```

## Period Locking (Prevent Edits to Closed Periods)

```javascript
/**
 * Installable onEdit trigger — reject edits to rows in locked periods.
 * Stores the lock date in Script Properties.
 */
function enforcePeriodLock(e) {
  var lockDate = PropertiesService.getScriptProperties().getProperty('periodLockDate');
  if (!lockDate) return;

  var sheet = e.source.getActiveSheet();
  if (sheet.getName() !== 'Journal') return;

  var editedRow = e.range.getRow();
  if (editedRow <= 1) return; // Header

  var rowDate = sheet.getRange(editedRow, 1).getValue();
  if (rowDate && new Date(rowDate) <= new Date(lockDate)) {
    e.range.setValue(e.oldValue || '');
    SpreadsheetApp.getUi().alert(
      'Cannot edit entries on or before ' + lockDate + ' — period is locked.'
    );
  }
}

function lockPeriod() {
  var ui = SpreadsheetApp.getUi();
  var response = ui.prompt('Lock Period', 'Enter cutoff date (YYYY-MM-DD):', ui.ButtonSet.OK_CANCEL);
  if (response.getSelectedButton() === ui.Button.OK) {
    PropertiesService.getScriptProperties().setProperty('periodLockDate', response.getResponseText());
    ui.alert('Period locked through ' + response.getResponseText());
  }
}
```

## Invoice Number Generator

```javascript
/**
 * Generate sequential invoice numbers with prefix.
 * Stores counter in Script Properties for persistence.
 */
function nextInvoiceNumber(prefix) {
  prefix = prefix || 'INV';
  var lock = LockService.getScriptLock();
  try {
    lock.waitLock(5000);
    var props = PropertiesService.getScriptProperties();
    var counter = parseInt(props.getProperty('invoiceCounter') || '0') + 1;
    props.setProperty('invoiceCounter', counter.toString());
    return prefix + '-' + ('00000' + counter).slice(-5); // INV-00001
  } finally {
    lock.releaseLock();
  }
}
```

## Tax Calculation Helper

```javascript
/**
 * Custom function: calculate tax amount.
 * Usage: =TAX(A2, 0.21) or =TAX(A2) for default rate
 */
function TAX(amount, rate) {
  rate = rate || parseFloat(PropertiesService.getScriptProperties().getProperty('defaultTaxRate') || '0.21');
  return Math.round(amount * rate * 100) / 100;
}

/**
 * Custom function: extract net amount from gross.
 * Usage: =NET(A2, 0.21)
 */
function NET(grossAmount, rate) {
  rate = rate || parseFloat(PropertiesService.getScriptProperties().getProperty('defaultTaxRate') || '0.21');
  return Math.round((grossAmount / (1 + rate)) * 100) / 100;
}
```

## Multi-Currency Support

```javascript
/**
 * Fetch live exchange rates and cache them.
 * Uses a free API — replace with your preferred provider.
 */
function getExchangeRate(from, to) {
  var cacheKey = 'fx_' + from + '_' + to;
  var cache = CacheService.getScriptCache();
  var cached = cache.get(cacheKey);
  if (cached) return parseFloat(cached);

  // Use your preferred FX API
  var apiKey = PropertiesService.getScriptProperties().getProperty('FX_API_KEY');
  var url = 'https://api.exchangerate-api.com/v4/latest/' + from;
  var response = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
  var data = JSON.parse(response.getContentText());
  var rate = data.rates[to];

  cache.put(cacheKey, rate.toString(), 3600); // Cache 1 hour
  return rate;
}

/**
 * Custom function: convert currency.
 * Usage: =FX(1000, "EUR", "USD")
 */
function FX(amount, from, to) {
  if (from === to) return amount;
  var rate = getExchangeRate(from, to);
  return Math.round(amount * rate * 100) / 100;
}
```

## Tips for Accounting Scripts

1. **Always validate double-entry balance** before posting journal entries
2. **Use `LockService`** for invoice number generation and any shared counter
3. **Use accounting number format** `$#,##0.00;($#,##0.00)` — shows negatives in parentheses
4. **Lock closed periods** to prevent accidental edits to finalized data
5. **Cache exchange rates** — don't fetch on every cell recalculation
6. **Custom functions have a 30-second limit** — keep them simple, use cached data
7. **Audit trail** — log who posted what and when using `Session.getActiveUser().getEmail()` and timestamps
8. **Back up before close** — use `DriveApp.getFileById(id).makeCopy()` to snapshot the workbook
