
# Product Requirements Document

# InvoXcel

## AI-Powered Invoice Extraction, Structuring & Export Platform

**Document Version:** 1.0  
**Product:** InvoXcel  
**Status:** Pre-development  
**Primary Goal:** MVP / Side Project

---

# 1. Product Overview

## 1.1 Product Name

**InvoXcel**

The name represents:

> **Invoice → Intelligent Extraction → Excel / Structured Data**

---

## 1.2 Product Vision

InvoXcel allows users to upload invoices in almost any common format and convert them into structured, editable data.

The system uses AI to understand invoice documents regardless of layout and extracts the fields selected by the user or defined by a template.

The user can then:

1. Review extracted data
2. Edit any extracted value
3. Add missing information
4. Review invoice line items
5. Export the final structured data

Supported export formats:

- XLSX
- CSV
- JSON
- QBO _(future / optional depending on implementation complexity)_

---

# 2. Problem Statement

Businesses receive invoices in many different formats:

- Digital PDFs
- Scanned PDFs
- Printed invoices
- Photographed invoices
- Computer-generated invoices
- Handwritten or partially handwritten invoices
- Different vendor layouts
- Multi-page invoices

Manual data entry from these documents into spreadsheets is repetitive and error-prone.

Existing invoice formats are inconsistent.

For example:

```
Vendor A:
Invoice No: A123

Vendor B:
Bill Number: 9912

Vendor C:
Document Reference: INV-88
```

The information means essentially the same thing but appears differently.

InvoXcel solves this by allowing AI to understand the invoice and map information into a **consistent user-selected schema**.

---

# 3. Core Product Principle

The most important architectural and product principle is:

> **The user chooses the desired output structure before extraction. AI extracts data into that structure.**

Instead of:

```
Upload
   ↓
AI decides everything
   ↓
Spreadsheet
```

InvoXcel should use:

```
Upload
   ↓
Analyze documents
   ↓
User chooses extraction columns
   ↓
AI extracts selected information
   ↓
Validation
   ↓
Editable workspace
   ↓
Export
```

This is the major improvement to our original plan.

---

# 4. Target Users

## Primary Users

### 1. Accountants

Need structured invoice information for bookkeeping.

### 2. Bookkeepers

Need to process many vendor invoices quickly.

### 3. Small Businesses

Need to organize invoices into Excel.

### 4. Finance Teams

Need structured invoice data for reporting and accounting systems.

### 5. Auditors

Need to review invoice data and compare financial information.

### 6. Data Entry Teams

Need to reduce repetitive manual entry.

---

# 5. Supported Input Formats

InvoXcel should support:

## Documents

- PDF
- Multi-page PDF
- JPG
- JPEG
- PNG

Potential future support:

- HEIC
- TIFF
- BMP

---

## Invoice Types

The system should attempt to process:

- Digital invoices
- Scanned invoices
- Printed invoices
- Phone photographs
- Computer-generated invoices
- Partially handwritten invoices
- Fully handwritten invoices
- Multi-page invoices
- Different invoice layouts

Important product rule:

> InvoXcel does not require users to create a separate template for every vendor layout.

The AI should interpret different invoice layouts and map them to the selected output schema.

This is also a core pattern emphasized by InvoiceXLSX: different vendor layouts and multi-page documents are handled without requiring a template per supplier. [InvoiceXLSX](https://invoicexlsx.com/)

---

# 6. High-Level Product Flow

The main user journey:

```
┌──────────────────────┐
│  1. Upload Files     │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│  2. Initial Analysis │
│                      │
│ AI understands the   │
│ uploaded documents   │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│  3. Select Columns   │
│                      │
│ Auto-detected or     │
│ Template-based       │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│  4. AI Extraction    │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│  5. Validation       │
│                      │
│ Totals / Tax / Dates │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│  6. Review & Edit    │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│  7. Export           │
│                      │
│ XLSX / CSV / JSON    │
└──────────────────────┘
```

---

# 7. Main Pages

Originally we planned two pages.

After studying this product pattern, I recommend **three primary product areas**.

```
1. Home / Upload
2. Processing Workspace
3. Templates
```

Admin functionality can initially live inside Django Admin.

---

# 8. PAGE 1 — Home / Upload

This remains the entry point.

## Purpose

Allow users to:

- Upload one or multiple invoices
- Select an existing template
- Create a new extraction session
- Add optional instructions

---

## UI Concept

```
INVOXCEL

Upload invoices and convert them
into structured, editable data.

┌──────────────────────────────────┐
│                                  │
│      Drag & Drop Invoices        │
│                                  │
│      PDF • JPG • PNG             │
│                                  │
└──────────────────────────────────┘

Uploaded Files

✓ invoice_001.pdf
✓ vendor_bill.jpg
✓ scan_2026.pdf


Template

[ Default Invoice Template       ▼ ]


Additional Instructions

┌──────────────────────────────────┐
│ Extract invoice data normally.   │
│                                  │
└──────────────────────────────────┘


[ Analyze Invoices ]
```

---

# 9. INITIAL ANALYSIS

This is the biggest change from our original plan.

The first AI stage should **not immediately perform final extraction**.

Instead:

```
Upload
↓
Initial Analysis
↓
Column Selection
↓
Final Extraction
```

---

## Purpose of Initial Analysis

The system analyzes the uploaded files and determines:

- Are these invoices?
- What information appears to exist?
- Are there line items?
- Are there tables?
- What standard fields are likely extractable?
- Are there unusual/custom fields?

For example:

```
Detected:

✓ Invoice Number
✓ Invoice Date
✓ Vendor Name
✓ Vendor GSTIN
✓ Buyer Name
✓ Currency
✓ Subtotal
✓ CGST
✓ SGST
✓ Total Amount
✓ Payment Terms

Line Items Detected: Yes
```

---

# 10. COLUMN SELECTION PAGE

The user should then see:

# Choose Columns to Extract

> Pick what you want InvoXcel to extract from your invoices.

---

## Auto-Detected Mode

The AI suggests fields based on the uploaded documents.

Example:

### Identifiers

```
☑ Invoice Number
☑ Invoice Date
☐ Due Date
☑ PO Number
```

---

### Vendor

```
☑ Vendor Name
☑ Vendor Address
☑ Vendor Tax ID
☐ Vendor Email
☐ Vendor Phone
```

---

### Buyer

```
☑ Buyer Name
☑ Buyer Address
☑ Buyer Tax ID
☐ Ship To
```

---

### Financial

```
☑ Currency
☑ Subtotal
☑ Discount
☑ Tax Amount
☑ Shipping
☑ Total Amount
☐ Amount Paid
☐ Balance Due
```

---

### Payment

```
☑ Payment Terms
☐ Payment Method
☐ Payment Status
```

---

### Other

```
☐ Notes
```

---

# 11. Manual Column Selection

Users should also be able to manually select fields.

Example:

```
Identifiers
Vendor
Buyer
Financial
Payment
Other
```

The user can select:

```
All
None
```

for each group.

This is useful because not every user wants every possible invoice field.

---

# 12. Custom Columns

This should be one of InvoXcel's important features.

Users can create custom columns.

Example:

```
Add Column

Column Name:

[ Project Code                ]

Field Type:

[ Text                        ▼ ]

[✓] Fill this in with AI
```

Possible field types:

- Text
- Number
- Currency
- Date
- Boolean

---

## AI-filled Custom Column

If enabled:

```
☑ Fill this in with AI
```

InvoXcel will instruct the AI:

> Extract or infer the value for Project Code from the invoice where possible.

---

## Manual Custom Column

If disabled:

```
☐ Fill this in with AI
```

The column exists but remains empty after processing.

The user can fill it manually later.

This is an excellent feature because it allows users to create an output spreadsheet that contains both:

```
AI extracted data
+
Manual business data
```

---

# 13. Line Item Selection

Line items should be treated separately from invoice summary data.

## Summary

One invoice has one summary record.

Example:

```
Invoice Number
Vendor
Date
Total
Tax
Currency
```

---

## Line Items

One invoice can have multiple line items.

Example:

|Description|Quantity|Unit Price|Tax|Amount|
|---|---|---|---|---|
|Product A|2|100|18%|236|
|Product B|1|500|18%|590|

---

The user should independently select line item fields:

```
☑ Description
☑ Quantity
☑ Unit Price
☑ Amount
☐ Tax Rate
☐ Tax Amount
☐ Unit
☐ Discount
```

This is important.

Do **not** mix the invoice summary schema and line-item schema internally.

---

# 14. Template System

This should become one of InvoXcel's core features.

## Default Template

Every new user gets access to:

> Default Invoice Template

Containing common invoice fields.

---

## User Templates

Users can create templates.

Example:

```
Templates

+ Create Template


My Templates

──────────────────────────

Standard Invoice
15 columns

GST Invoice India
22 columns

Vendor Expense Import
18 columns

QuickBooks Import
12 columns
```

---

# 15. Create Template Flow

```
Template Name

[ Indian GST Invoice              ]


Summary Columns

☑ Invoice Number
☑ Invoice Date
☑ Vendor Name
☑ Vendor GSTIN
☑ Customer Name
☑ Customer GSTIN
☑ Taxable Amount
☑ CGST
☑ SGST
☑ IGST
☑ Grand Total


Line Item Columns

☑ Description
☑ Quantity
☑ Unit Price
☑ Amount
```

Then:

```
[ Save Template ]
```

---

## Important Design Decision

A template should represent:

```
What data the user wants
```

Not:

```
What an individual vendor's invoice looks like
```

This distinction is critical.

Bad template concept:

```
Amazon Invoice Template
ABC Traders Template
Vendor XYZ Template
```

Better:

```
Indian GST Template
Accounting Import Template
Expense Report Template
QuickBooks Template
Custom Company Template
```

AI handles vendor layout differences.

Templates define the output structure.

---

# 16. Processing Stage

Once the user confirms the selected columns:

```
[ Extract Data ]
```

The system creates a processing batch.

```
Batch Created

23 Files

Processing...

██████████████░░░░  72%

17 / 23 invoices complete
```

---

# 17. AI Extraction Strategy

The system should not ask Gemini:

> "Read this invoice and tell me everything."

Instead, the system should dynamically generate the extraction request based on the selected template.

Example:

```
Extract the following invoice fields:

Invoice Number
Invoice Date
Vendor Name
Vendor GSTIN
Currency
Subtotal
CGST
SGST
IGST
Grand Total

Also extract these line item fields:

Description
Quantity
Unit Price
Amount

Return structured JSON only.
```

This makes processing:

- More focused
- More predictable
- Cheaper
- Easier to validate

---

# 18. Structured Output Model

Internally, every processed invoice should conceptually become:

```
{
  "invoice": {
    "invoice_number": "...",
    "invoice_date": "...",
    "vendor_name": "...",
    "currency": "...",
    "subtotal": 0,
    "tax_amount": 0,
    "total_amount": 0
  },

  "line_items": [
    {
      "description": "...",
      "quantity": 0,
      "unit_price": 0,
      "amount": 0
    }
  ]
}
```

Then InvoXcel maps this internal data to the selected template.

This separation is extremely important.

```
AI Extraction Schema
        ↓
Normalized Invoice Data
        ↓
Template Mapping
        ↓
User Workspace
        ↓
Export Format
```

---

# 19. PAGE 2 — Processing Results Workspace

After extraction, the user enters the main workspace.

Example navigation:

```
INVOXCEL

Invoices     Templates

────────────────────────────────────

23 Invoices Processed

[ Columns ] [ Customize Columns ]

[ Summary ] [ Line Items ]

                    Export

       [ XLSX ] [ CSV ] [ JSON ]
```

---

# 20. Invoice Summary Table

Example:

|#|Invoice Number|Invoice Date|Vendor|Currency|Tax|Total|
|---|---|---|---|---|---|---|
|1|A4587|12-09-2026|ABC Traders|INR|4,410|29,160|
|2|B1258|13-09-2026|Kerala Agencies|INR|3,240|21,240|

---

## Table Features

Users should be able to:

- Edit any cell
- Search
- Sort
- Filter
- Add rows
- Delete rows
- Hide columns
- Reorder columns
- Change visible columns

Later:

- Bulk edit
- Copy/paste from Excel
- Keyboard navigation

---

# 21. Invoice Detail / Source View

This is a feature I strongly recommend adding.

When the user clicks an invoice:

```
┌────────────────────┬────────────────────┐
│                    │                    │
│   SOURCE INVOICE   │   EXTRACTED DATA   │
│                    │                    │
│   PDF Preview      │ Invoice Number     │
│                    │ [ A4587         ]  │
│                    │                    │
│                    │ Vendor             │
│                    │ [ ABC Traders   ]  │
│                    │                    │
│                    │ Total              │
│                    │ [ 29160         ]  │
│                    │                    │
└────────────────────┴────────────────────┘
```

This makes manual verification much easier.

The user can compare:

```
Original Invoice
        ↔
Extracted Data
```

This should be more valuable than a complicated chat interface.

---

# 22. Line Item View

The user should be able to expand an invoice.

Example:

```
Invoice A4587

[ Hide 18 Line Items ]
```

Then:

|Description|Quantity|Unit Price|Amount|
|---|---|---|---|
|Amazon Bedrock|1|5.87|5.87|
|Route 53|1|1.18|1.18|
|EC2|1|0.00|0.00|

This should support:

- Add line item
- Edit line item
- Delete line item

---

# 23. Summary and Line Items Should Be Separate Views

This should be a product rule.

```
[ Summary ]   [ Line Items ]
```

Why?

Because:

```
Invoice Summary

1 row = 1 invoice
```

while:

```
Line Items

1 row = 1 purchased item
```

Mixing these in one giant table becomes difficult.

However, export can optionally flatten data later.

---

# 24. Data Validation Layer

This is something our original concept had that should remain.

AI extraction alone is not enough.

InvoXcel should validate:

### Dates

```
Valid date format?
Future date?
Due date before invoice date?
```

### Currency

```
INR
USD
EUR
etc.
```

### Numeric Values

```
Can text be converted into a valid number?
```

### Tax

For India-specific templates:

```
CGST
SGST
IGST
GSTIN validation
```

### Totals

```
Calculated Total

=
Subtotal
- Discount
+ Tax
+ Shipping
+ Other Charges
```

Compare with:

```
Extracted Total
```

---

# 25. Verification Status

Every invoice can receive a status.

Recommended statuses:

```
APPROVED

REVIEW RECOMMENDED

REVIEW REQUIRED

FAILED
```

Example logic:

### Approved

```
All required fields present
+
Totals match
+
Data formats valid
```

### Review Recommended

```
Minor inconsistency
or
Medium extraction confidence
```

### Review Required

```
Total mismatch
Missing required field
Unreadable document
Invalid important data
```

### Failed

```
Document could not be processed
```

---

# 26. Confidence

I would slightly redesign our original `Confidence %` concept.

Instead of relying only on Gemini's self-reported confidence:

```
AI Confidence
+
Validation Confidence
=
Final Confidence Score
```

For example:

```
AI found Invoice Number        +10
AI found Vendor                +10
AI found Date                  +10
AI found Total                 +15
Line items successfully parsed +15
Total calculation matches      +20
Tax validation successful      +10
Required fields complete       +10
```

This produces a more useful internal confidence score.

---

# 27. Export System

## MVP Export Formats

### XLSX

Primary export.

### CSV

Simple data export.

### JSON

Useful for developers and integrations.

---

## Future

### QBO

QuickBooks-oriented export.

I recommend not putting QBO in the first MVP unless you specifically need it.

It introduces accounting-format requirements that are unrelated to proving the main product.

---

# 28. XLSX Export Structure

Depending on the template, XLSX should support multiple sheets.

Example:

```
Invoice_Export.xlsx

Sheet 1
Invoice Summary

Sheet 2
Line Items

Sheet 3
Validation Report (optional)
```

This is better than forcing everything into one flat spreadsheet.

---

# 29. CSV Export

Because CSV does not support multiple sheets, provide:

### Option A

```
Summary CSV
```

### Option B

```
Line Items CSV
```

Or export a ZIP containing both later.

For MVP:

```
Export Summary CSV
Export Line Items CSV
```

---

# 30. JSON Export

Example:

```
{
  "batch_id": "batch_001",
  "invoices": [
    {
      "invoice_number": "A4587",
      "vendor_name": "ABC Traders",
      "total": 29160,
      "line_items": []
    }
  ]
}
```

---

# 31. User Roles

## Normal User

Can:

- Upload files
- Create processing batches
- Create templates
- Edit own extracted data
- Export own data
- Delete own data

Cannot:

- View other users
- View other users' invoices
- Manage system settings

---

## Admin

Can:

- Manage users
- View all batches
- View failed jobs
- Inspect AI errors
- Inspect processing usage
- Delete files
- Manage system configuration

For the MVP:

> Use Django Admin rather than building a separate custom admin interface.

---

# 32. Processing History

I recommend adding an Invoices / History page.

```
My Batches

September Expenses
23 invoices
Completed

August Vendor Bills
48 invoices
Completed

Test Batch
3 invoices
Failed
```

This makes the application feel like a real product rather than a one-time converter.

---

# 33. Recommended Product Navigation

```
INVOXCEL

Home

Invoices
    ├── All Batches
    └── Batch Workspace

Templates

Profile
```

Admin users additionally have Django Admin.

---

# 34. Core MVP Features

These are the features I would definitely build.

## Upload

- Multiple files
- PDF
- JPG
- PNG

## Initial Analysis

- Identify invoice documents
- Detect common fields
- Detect line items

## Column Selection

- Auto-detected fields
- Manual selection
- Categories
- Select all
- Select none

## Custom Columns

- Text
- Number
- Date
- Currency
- AI extraction toggle

## Templates

- Default template
- Create template
- Edit template
- Delete template

## AI Extraction

- Extract selected fields
- Extract selected line items
- Return structured data

## Validation

- Dates
- Numeric fields
- Totals
- Required fields

## Review Workspace

- Summary table
- Line item table
- Inline editing
- Add/delete rows
- Search
- Filter

## Export

- XLSX
- CSV
- JSON

---

# 35. Features to Explicitly Avoid in MVP

To start fast, do **not** build:

- Smart reports
- Expense categorization
- Cost center AI classification
- Duplicate invoice detection
- Accounting software integrations
- API for third parties
- Team collaboration
- Comments
- Audit trails
- QBO export
- Advanced analytics
- Complex chat memory

These can be Version 2.

---

# 36. Version 2 Roadmap

Once the MVP works:

## Phase 2

```
QBO Export

QuickBooks Template

Xero Template

Zoho Template

GST-specific Template Improvements
```

## Phase 3

```
AI Smart Reports

Spend Categorization

Duplicate Detection

Vendor Analytics

Monthly Reports
```

## Phase 4

```
Public API

Accounting Integrations

Webhooks

Team Workspaces

Roles and Permissions
```

---

# 37. Revised Core System Concept

The final InvoXcel concept should be:

```
                    INVOXCEL

       Upload invoices in any common format
                        ↓
              AI analyzes documents
                        ↓
          User selects desired columns
                        ↓
             Select or create template
                        ↓
          AI extracts structured data
                        ↓
           Validation & normalization
                        ↓
         Editable invoice data workspace
                        ↓
             Summary + Line Items
                        ↓
       XLSX / CSV / JSON / Future QBO
```

---

# 38. The Most Important Product Decision

I believe the single best decision for InvoXcel is this:

## InvoXcel should be template-driven, not fixed-schema-driven.

Your original output was a fixed table:

```
Invoice ID
Invoice Number
Invoice Date
Vendor Name
Vendor GSTIN
...
```

That is still useful as your **default template**.

But the product itself should support:

```
Template A

Invoice Number
Vendor
Total
```

or:

```
Template B

Invoice Number
Vendor GSTIN
PO Number
CGST
SGST
IGST
```

or:

```
Template C

Project Code
Department
Invoice Number
Vendor
Total
Approval Status
```

This makes InvoXcel substantially more flexible without requiring you to reinvent invoice extraction.

---

# 39. Final MVP Definition

If I had to define InvoXcel in one sentence:

> **InvoXcel is an AI-powered invoice processing workspace where users upload invoices in any common format, choose the data structure they need, extract invoice and line-item information with AI, review and edit the results, and export clean structured data.**

---

# My recommended next planning step

Before writing any code, I would now lock these **four documents**, in this order:

### 1. Product flow specification

Every screen and transition:

```
Upload
→ Analysis
→ Column Selection
→ Extraction
→ Results Workspace
→ Export
```

### 2. Template and column system specification

This is now the heart of InvoXcel.

We need to precisely define:

- Standard columns
- Custom columns
- Data types
- Required fields
- AI extraction behavior
- Summary vs line-item columns

### 3. Database model and relationships

Especially:

```
User
Template
TemplateColumn
Batch
SourceFile
Invoice
InvoiceFieldValue
LineItem
LineItemFieldValue
```

### 4. AI extraction and validation specification

Exactly what happens during:

```
Initial Analysis
vs
Final Extraction
vs
Validation
```

**My strongest recommendation is that we do the next step as a complete product blueprint of the screen flow and template/column system before discussing Django models.** That will prevent the database design from locking us into the wrong product structure.