# Apps Script Patterns for Software Consultancy Billing

## Timesheet → Invoice Pipeline

```javascript
/**
 * Generate an invoice from approved timesheet entries for a client/project.
 * Timesheets columns: [Date, Consultant, Client, Project, Hours, Rate, Status, InvoiceID]
 * Status values: Pending, Approved, Invoiced
 */
function generateInvoiceFromTimesheets(clientName, periodStart, periodEnd) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var timesheets = ss.getSheetByName('Timesheets');
  var invoices = ss.getSheetByName('Invoices');
  var data = timesheets.getDataRange().getValues();

  var start = new Date(periodStart);
  var end = new Date(periodEnd);
  var lineItems = [];
  var matchedRows = [];

  for (var i = 1; i < data.length; i++) {
    var rowDate = new Date(data[i][0]);
    var client = data[i][2];
    var status = data[i][6];

    if (client === clientName && status === 'Approved' &&
        rowDate >= start && rowDate <= end) {
      lineItems.push({
        date: data[i][0],
        consultant: data[i][1],
        project: data[i][3],
        hours: parseFloat(data[i][4]),
        rate: parseFloat(data[i][5]),
        row: i
      });
      matchedRows.push(i);
    }
  }

  if (lineItems.length === 0) {
    SpreadsheetApp.getUi().alert('No approved timesheet entries found for ' +
      clientName + ' in the selected period.');
    return;
  }

  // Group by consultant + project for the invoice
  var grouped = {};
  lineItems.forEach(function(item) {
    var key = item.consultant + '|' + item.project;
    if (!grouped[key]) {
      grouped[key] = { consultant: item.consultant, project: item.project, hours: 0, rate: item.rate };
    }
    grouped[key].hours += item.hours;
  });

  // Generate invoice number
  var invoiceNum = nextInvoiceNumber('INV');
  var subtotal = 0;

  // Write invoice line items
  Object.keys(grouped).forEach(function(key) {
    var g = grouped[key];
    var lineTotal = g.hours * g.rate;
    subtotal += lineTotal;
    invoices.appendRow([
      invoiceNum, new Date(), clientName, g.consultant, g.project,
      g.hours, g.rate, lineTotal, '', 'Unpaid'
    ]);
  });

  // Mark timesheet entries as invoiced
  matchedRows.forEach(function(row) {
    data[row][6] = 'Invoiced';
    data[row][7] = invoiceNum;
  });
  timesheets.getDataRange().setValues(data);

  return { invoiceNumber: invoiceNum, lineItems: Object.keys(grouped).length, subtotal: subtotal };
}
```

## Billable Hours Tracker with Utilization

```javascript
/**
 * Calculate utilization rates per consultant for a given month.
 * Assumes 8 billable hours/day target, ~22 working days/month = 176 target hours.
 * Timesheets columns: [Date, Consultant, Client, Project, Hours, Rate, Status, InvoiceID]
 */
function generateUtilizationReport(year, month) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var data = ss.getSheetByName('Timesheets').getDataRange().getValues();
  var consultants = ss.getSheetByName('Consultants');
  var consultantData = consultants.getDataRange().getValues();

  // Build target hours map from Consultants sheet
  // Consultants columns: [Name, Role, MonthlyTargetHours, CostRate]
  var targets = {};
  for (var c = 1; c < consultantData.length; c++) {
    targets[consultantData[c][0]] = {
      role: consultantData[c][1],
      targetHours: parseFloat(consultantData[c][2]) || 176,
      costRate: parseFloat(consultantData[c][3]) || 0
    };
  }

  var utilization = {};

  for (var i = 1; i < data.length; i++) {
    var rowDate = new Date(data[i][0]);
    if (rowDate.getFullYear() !== year || rowDate.getMonth() !== month - 1) continue;

    var consultant = data[i][1];
    var hours = parseFloat(data[i][4]) || 0;
    var rate = parseFloat(data[i][5]) || 0;

    if (!utilization[consultant]) {
      utilization[consultant] = { billableHours: 0, revenue: 0 };
    }
    utilization[consultant].billableHours += hours;
    utilization[consultant].revenue += hours * rate;
  }

  // Write report
  var report = ss.getSheetByName('Utilization') || ss.insertSheet('Utilization');
  report.clear();
  report.appendRow([
    'Consultant', 'Role', 'Billable Hours', 'Target Hours',
    'Utilization %', 'Revenue', 'Cost', 'Margin', 'Margin %'
  ]);

  Object.keys(utilization).sort().forEach(function(name) {
    var u = utilization[name];
    var t = targets[name] || { role: '', targetHours: 176, costRate: 0 };
    var utilizationPct = u.billableHours / t.targetHours;
    var cost = u.billableHours * t.costRate;
    var margin = u.revenue - cost;
    var marginPct = u.revenue > 0 ? margin / u.revenue : 0;

    report.appendRow([
      name, t.role, u.billableHours, t.targetHours,
      utilizationPct, u.revenue, cost, margin, marginPct
    ]);
  });

  // Format
  var lastRow = report.getLastRow();
  report.getRange(2, 5, lastRow - 1, 1).setNumberFormat('0.0%');
  report.getRange(2, 6, lastRow - 1, 3).setNumberFormat('$#,##0.00;($#,##0.00)');
  report.getRange(2, 9, lastRow - 1, 1).setNumberFormat('0.0%');
  report.getRange(1, 1, 1, 9).setFontWeight('bold');
  report.autoResizeColumns(1, 9);
}
```

## Project Profitability Dashboard

```javascript
/**
 * Calculate profitability per client/project.
 * Crosses timesheet revenue against internal costs and external expenses.
 */
function generateProfitabilityReport() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var timesheets = ss.getSheetByName('Timesheets').getDataRange().getValues();
  var expenses = ss.getSheetByName('Project Expenses').getDataRange().getValues();
  var consultantData = ss.getSheetByName('Consultants').getDataRange().getValues();

  // Build cost rate map
  var costRates = {};
  for (var c = 1; c < consultantData.length; c++) {
    costRates[consultantData[c][0]] = parseFloat(consultantData[c][3]) || 0;
  }

  // Aggregate by client + project
  var projects = {};

  // Revenue and internal cost from timesheets
  for (var i = 1; i < timesheets.length; i++) {
    var client = timesheets[i][2];
    var project = timesheets[i][3];
    var consultant = timesheets[i][1];
    var hours = parseFloat(timesheets[i][4]) || 0;
    var billRate = parseFloat(timesheets[i][5]) || 0;
    var key = client + ' | ' + project;

    if (!projects[key]) {
      projects[key] = { client: client, project: project, revenue: 0, internalCost: 0,
                        externalCost: 0, hours: 0 };
    }
    projects[key].revenue += hours * billRate;
    projects[key].internalCost += hours * (costRates[consultant] || 0);
    projects[key].hours += hours;
  }

  // External costs (contractors, SaaS, infra)
  // Expenses columns: [Date, Client, Project, Category, Description, Amount]
  for (var e = 1; e < expenses.length; e++) {
    var key = expenses[e][1] + ' | ' + expenses[e][2];
    if (!projects[key]) {
      projects[key] = { client: expenses[e][1], project: expenses[e][2],
                        revenue: 0, internalCost: 0, externalCost: 0, hours: 0 };
    }
    projects[key].externalCost += parseFloat(expenses[e][5]) || 0;
  }

  // Write report
  var report = ss.getSheetByName('Profitability') || ss.insertSheet('Profitability');
  report.clear();
  report.appendRow([
    'Client', 'Project', 'Hours', 'Revenue',
    'Internal Cost', 'External Cost', 'Total Cost',
    'Gross Profit', 'Margin %'
  ]);

  Object.keys(projects).sort().forEach(function(key) {
    var p = projects[key];
    var totalCost = p.internalCost + p.externalCost;
    var profit = p.revenue - totalCost;
    var margin = p.revenue > 0 ? profit / p.revenue : 0;

    report.appendRow([
      p.client, p.project, p.hours, p.revenue,
      p.internalCost, p.externalCost, totalCost,
      profit, margin
    ]);
  });

  var lastRow = report.getLastRow();
  report.getRange(2, 4, lastRow - 1, 5).setNumberFormat('$#,##0.00;($#,##0.00)');
  report.getRange(2, 9, lastRow - 1, 1).setNumberFormat('0.0%');
  report.getRange(1, 1, 1, 9).setFontWeight('bold');
  report.autoResizeColumns(1, 9);

  // Conditional format: red margin if below 20%
  var marginRange = report.getRange(2, 9, lastRow - 1, 1);
  var rule = SpreadsheetApp.newConditionalFormatRule()
    .whenNumberLessThan(0.2)
    .setBackground('#FFCDD2')
    .setRanges([marginRange])
    .build();
  report.setConditionalFormatRules([rule]);
}
```

## Retainer Tracking

```javascript
/**
 * Track monthly retainer usage per client.
 * Retainers sheet: [Client, MonthlyHours, MonthlyRate, RolloverPolicy]
 * RolloverPolicy: "none", "cap:20" (rollover up to 20hrs), "unlimited"
 */
function updateRetainerUsage(year, month) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var retainers = ss.getSheetByName('Retainers').getDataRange().getValues();
  var timesheets = ss.getSheetByName('Timesheets').getDataRange().getValues();

  // Sum hours per retainer client for the month
  var usage = {};
  for (var i = 1; i < timesheets.length; i++) {
    var d = new Date(timesheets[i][0]);
    if (d.getFullYear() !== year || d.getMonth() !== month - 1) continue;
    var client = timesheets[i][2];
    usage[client] = (usage[client] || 0) + (parseFloat(timesheets[i][4]) || 0);
  }

  var report = ss.getSheetByName('Retainer Usage') || ss.insertSheet('Retainer Usage');
  report.clear();
  report.appendRow([
    'Client', 'Retainer Hours', 'Used Hours', 'Remaining',
    'Overage Hours', 'Monthly Fee', 'Overage Fee', 'Total Due'
  ]);

  for (var r = 1; r < retainers.length; r++) {
    var client = retainers[r][0];
    var monthlyHours = parseFloat(retainers[r][1]);
    var monthlyRate = parseFloat(retainers[r][2]);
    var hourlyRate = monthlyRate / monthlyHours;
    var used = usage[client] || 0;
    var remaining = Math.max(0, monthlyHours - used);
    var overage = Math.max(0, used - monthlyHours);
    var overageFee = overage * hourlyRate * 1.25; // 25% premium on overage
    var totalDue = monthlyRate + overageFee;

    report.appendRow([
      client, monthlyHours, used, remaining,
      overage, monthlyRate, overageFee, totalDue
    ]);
  }

  var lastRow = report.getLastRow();
  report.getRange(2, 6, lastRow - 1, 3).setNumberFormat('$#,##0.00');
  report.getRange(1, 1, 1, 8).setFontWeight('bold');
  report.autoResizeColumns(1, 8);
}
```

## Client Rate Card Management

```javascript
/**
 * Look up the billing rate for a consultant on a given client/project.
 * Rate Cards sheet: [Client, Project, Role, HourlyRate, EffectiveFrom, EffectiveTo]
 * Falls back to default rate if no specific rate card exists.
 */
function getBillingRate(client, project, role, date) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var rateCards = ss.getSheetByName('Rate Cards').getDataRange().getValues();
  date = date || new Date();

  var bestMatch = null;
  var defaultRate = null;

  for (var i = 1; i < rateCards.length; i++) {
    var rcClient = rateCards[i][0];
    var rcProject = rateCards[i][1];
    var rcRole = rateCards[i][2];
    var rcRate = parseFloat(rateCards[i][3]);
    var from = rateCards[i][4] ? new Date(rateCards[i][4]) : new Date(0);
    var to = rateCards[i][5] ? new Date(rateCards[i][5]) : new Date(9999, 0);

    if (date < from || date > to) continue;

    // Exact match: client + project + role
    if (rcClient === client && rcProject === project && rcRole === role) {
      return rcRate;
    }
    // Client + role match (any project)
    if (rcClient === client && rcProject === '' && rcRole === role) {
      bestMatch = rcRate;
    }
    // Default for role
    if (rcClient === '' && rcRole === role) {
      defaultRate = rcRate;
    }
  }

  return bestMatch || defaultRate || 0;
}
```

## Expense Allocation Across Projects

```javascript
/**
 * Allocate shared costs (SaaS tools, infra, office) proportionally
 * across active projects based on billable hours share.
 *
 * Shared Costs sheet: [Month, Category, Description, Amount]
 * Writes to: Cost Allocation sheet
 */
function allocateSharedCosts(year, month) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var timesheets = ss.getSheetByName('Timesheets').getDataRange().getValues();
  var sharedCosts = ss.getSheetByName('Shared Costs').getDataRange().getValues();

  // Calculate hours per project for the month
  var projectHours = {};
  var totalHours = 0;

  for (var i = 1; i < timesheets.length; i++) {
    var d = new Date(timesheets[i][0]);
    if (d.getFullYear() !== year || d.getMonth() !== month - 1) continue;
    var key = timesheets[i][2] + ' | ' + timesheets[i][3];
    var hours = parseFloat(timesheets[i][4]) || 0;
    projectHours[key] = (projectHours[key] || 0) + hours;
    totalHours += hours;
  }

  if (totalHours === 0) return;

  // Get shared costs for the month
  var monthCosts = [];
  for (var c = 1; c < sharedCosts.length; c++) {
    var costMonth = sharedCosts[c][0];
    if (costMonth === year + '-' + ('0' + month).slice(-2)) {
      monthCosts.push({
        category: sharedCosts[c][1],
        description: sharedCosts[c][2],
        amount: parseFloat(sharedCosts[c][3])
      });
    }
  }

  // Allocate
  var report = ss.getSheetByName('Cost Allocation') || ss.insertSheet('Cost Allocation');
  report.clear();
  report.appendRow(['Project', 'Cost Category', 'Description', 'Hours Share %', 'Allocated Amount']);

  Object.keys(projectHours).sort().forEach(function(project) {
    var share = projectHours[project] / totalHours;
    monthCosts.forEach(function(cost) {
      report.appendRow([
        project, cost.category, cost.description,
        share, cost.amount * share
      ]);
    });
  });

  var lastRow = report.getLastRow();
  report.getRange(2, 4, lastRow - 1, 1).setNumberFormat('0.0%');
  report.getRange(2, 5, lastRow - 1, 1).setNumberFormat('$#,##0.00');
  report.getRange(1, 1, 1, 5).setFontWeight('bold');
  report.autoResizeColumns(1, 5);
}
```

## Automated Monthly Invoice Email

```javascript
/**
 * Send invoice summary email to client contacts.
 * Requires an installable trigger (uses GmailApp).
 * Client Contacts sheet: [Client, ContactName, Email, SendInvoices]
 */
function emailInvoiceSummary(invoiceNumber) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var invoices = ss.getSheetByName('Invoices').getDataRange().getValues();
  var contacts = ss.getSheetByName('Client Contacts').getDataRange().getValues();

  // Gather invoice line items
  var lines = [];
  var client = '';
  var total = 0;

  for (var i = 1; i < invoices.length; i++) {
    if (invoices[i][0] === invoiceNumber) {
      client = invoices[i][2];
      lines.push({
        consultant: invoices[i][3],
        project: invoices[i][4],
        hours: invoices[i][5],
        rate: invoices[i][6],
        amount: invoices[i][7]
      });
      total += parseFloat(invoices[i][7]);
    }
  }

  // Find contact
  var recipientEmail = '';
  var contactName = '';
  for (var c = 1; c < contacts.length; c++) {
    if (contacts[c][0] === client && contacts[c][3] === true) {
      recipientEmail = contacts[c][2];
      contactName = contacts[c][1];
      break;
    }
  }

  if (!recipientEmail) {
    Logger.log('No invoice contact found for ' + client);
    return;
  }

  // Build email
  var template = HtmlService.createTemplateFromFile('InvoiceEmail');
  template.contactName = contactName;
  template.invoiceNumber = invoiceNumber;
  template.client = client;
  template.lines = lines;
  template.total = total;
  template.dueDate = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000); // Net 30

  GmailApp.sendEmail(recipientEmail, 'Invoice ' + invoiceNumber + ' — ' + client, '', {
    htmlBody: template.evaluate().getContent(),
    name: PropertiesService.getScriptProperties().getProperty('companyName') || 'Accounts'
  });

  Logger.log('Invoice email sent to ' + recipientEmail + ' for ' + invoiceNumber);
}
```

## Payment Tracking & Aging

```javascript
/**
 * Update payment status and calculate days outstanding.
 * Invoice Summary columns: [InvoiceNum, Client, IssueDate, DueDate, Amount, PaidDate, PaidAmount, Status]
 */
function updatePaymentStatus() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('Invoice Summary');
  var data = sheet.getDataRange().getValues();
  var today = new Date();

  for (var i = 1; i < data.length; i++) {
    var dueDate = new Date(data[i][3]);
    var amount = parseFloat(data[i][4]);
    var paidAmount = parseFloat(data[i][6]) || 0;
    var paidDate = data[i][5];

    if (paidAmount >= amount) {
      data[i][7] = 'Paid';
    } else if (paidAmount > 0) {
      data[i][7] = 'Partial (' + Math.round(paidAmount / amount * 100) + '%)';
    } else if (today > dueDate) {
      var daysLate = Math.floor((today - dueDate) / (1000 * 60 * 60 * 24));
      data[i][7] = 'Overdue ' + daysLate + ' days';
    } else {
      data[i][7] = 'Pending';
    }
  }

  sheet.getDataRange().setValues(data);
}
```

## Consultancy Accounting Menu

```javascript
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Consultancy')
    .addItem('Log Time Entry...', 'showTimeEntryDialog')
    .addItem('Approve Selected Timesheets', 'approveSelectedRows')
    .addSeparator()
    .addSubMenu(SpreadsheetApp.getUi().createMenu('Invoicing')
      .addItem('Generate Invoice from Timesheets...', 'showInvoiceDialog')
      .addItem('Update Payment Status', 'updatePaymentStatus')
      .addItem('Email Invoice...', 'showEmailInvoiceDialog'))
    .addSeparator()
    .addSubMenu(SpreadsheetApp.getUi().createMenu('Reports')
      .addItem('Utilization Report...', 'showUtilizationDialog')
      .addItem('Project Profitability', 'generateProfitabilityReport')
      .addItem('Retainer Usage...', 'showRetainerDialog')
      .addItem('AR Aging Report', 'generateAgingReport')
      .addItem('Cost Allocation...', 'showCostAllocationDialog'))
    .addSeparator()
    .addSubMenu(SpreadsheetApp.getUi().createMenu('Period')
      .addItem('Lock Period...', 'lockPeriod')
      .addItem('Run Close Checklist', 'runCloseChecklist'))
    .addToUi();
}
```

## Tips for Software Consultancy Accounting

1. **Timesheet approval workflow** — never auto-invoice unapproved hours; add an Approved/Invoiced status column
2. **Rate card versioning** — store effective dates so historical invoices remain accurate
3. **Retainer overage** — clearly define the overage rate (common: 1.25x or 1.5x) in the retainer sheet, not hardcoded
4. **Separate internal vs external costs** — internal = consultant salary cost; external = contractors, SaaS, infra allocated to client
5. **LockService on invoice numbers** — concurrent invoice generation can produce duplicate numbers without it
6. **Net payment terms** — store per-client (Net 15, Net 30, Net 60) in the Client Contacts sheet
7. **Multi-currency clients** — cache exchange rates at invoice generation time and store the rate used on the invoice for audit
8. **Audit trail** — log all invoice generation and email sends with timestamps using `console.log()` (goes to Cloud Logging)
9. **Period close** — lock the period after reconciliation to prevent retroactive timesheet edits
10. **Data validation** — use Sheets data validation (dropdown lists) for client names, project codes, and consultant names to prevent typos
