# Expense Attachments Downloader

**Author:** Martel Innovate IT
**Version:** 18.0.1.0.0
**Category:** Human Resources / Expenses
**Depends:** `base`, `hr_expense`

## Description

Adds a **"Attachments"** action to the expense report list/form view. Clicking it merges all attachments (PDF and images) of the selected expense report into a single PDF file, which is streamed directly to the browser for download.

No intermediate file is stored in the database or on the filesystem — the merged PDF is generated in memory and streamed directly to the client.

## Features

- Merges all attachments from an expense report into a single PDF
- Supported input formats: `PDF`, `JPEG`, `PNG`, `JPG`
- Dynamic filename: `Expense Report - <Employee Name> - <Report ID>.pdf`
- Accessible only to users in the **Expense Manager** group
- Unsupported file formats raise a clear error message with the filename

## Installation

### Python dependencies

Install via pip (or let Odoo pick up `requirements.txt`):

```bash
pip install Pillow==12.1.1 pypdf==6.9.1
```

### Module installation

1. Copy the `custom_download_attachments` folder into your Odoo addons path
2. Restart Odoo and update the module list
3. Install **Expense Attachments Downloader** from the Apps menu

## Usage

1. Go to **Expenses → Expense Reports**
2. Select one or more expense reports
3. Open **Action → Attachments**
4. The merged PDF downloads automatically in the browser

> **Note:** only users belonging to the *Expense Manager* group can use this feature.

## Security

- The download endpoint (`/download/expense_attachments`) requires an authenticated session
- An explicit group check (`hr_expense.group_hr_expense_manager`) blocks non-managers with HTTP 403
- Record access uses `search()` (ORM rules enforced) instead of `browse()`, preventing IDOR attacks

## Changelog

### 18.0.1.0.0
- Migrated to Odoo 18
- Replaced deprecated `PyPDF2` with `pypdf` (new API: `PdfWriter`, `PdfReader`, `.pages`, `.add_page()`)
- Fixed critical security bug: added explicit Expense Manager group check on the HTTP endpoint
- Fixed IDOR vulnerability: replaced `.browse()` with `.search()` to enforce `ir.rule` record rules
- Removed invalid `assets` block from manifest (Python files are not web assets)
- Pinned dependency versions for reproducible builds

### 16.0.1.0.0
- Initial release for Odoo 16
