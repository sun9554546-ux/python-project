# LibTrack — Library Book Usage Analysis System

A Flask + MySQL library website with a public book catalogue and a separate admin dashboard. The small floating book button on the public website opens the admin password dialog.

## Features
- Public book catalogue with title/author/ISBN search and availability counts.
- Separate borrower loan-history lookup.
- Floating book icon opens admin login from the same public website.
- Admin dashboard with editable inventory, physical/damaged/missing copy tracking, CSV book import, student account controls and borrowing limits.
- Circulation tools for issue, return, 7-day renewal, reservation approval/rejection, overdue monitoring and QR scanning.
- Analytics for monthly borrowing, categories, popular books, most active readers, rarely borrowed books, and daily/weekly/monthly totals.
- CSV and PDF report export, searchable inventory, responsive layout, and saved dark/light theme preference.

## Windows 11 setup (VS Code + MySQL Workbench)

1. Install Python 3.11+ and MySQL Server 8.0. Start the MySQL80 service.
2. Extract this ZIP to a simple folder, for example `K:\Library_Book_Usage_Analysis_System`.
3. Open that folder in VS Code and open Terminal → New Terminal.
4. Create and activate a virtual environment:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
   If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal, then activate again.
5. Install dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```
6. In MySQL Workbench, open `schema.sql` and execute it. It creates `library_analysis` and adds sample books. If you already have a database from the previous ZIP, run `migrate_existing_database.sql` instead to add the new columns and reservation table.
7. Copy `.env.example` to `.env`. Set `DB_PASSWORD` to the password you chose for MySQL `root`. Keep `DB_NAME=library_analysis`. For a local demo, the admin password is `1234`.
8. Start the website:
   ```powershell
   python app.py
   ```
9. Open `http://127.0.0.1:5000` in your browser. Click the floating book icon at the bottom-right and enter `1234` to open the admin dashboard.

## Important notes
- `1234` is intentionally a demo password. Change `ADMIN_PASSWORD` in `.env` before exposing the app to a network. The server checks the password; it is not only a browser-side check.
- Never upload your `.env` file or share your database password.
- If the page reports a database connection error, verify MySQL is running, `.env` credentials are correct, and `schema.sql` was executed successfully.
- Test the database connection by visiting `http://127.0.0.1:5000/health` while the app is running.
- This is a local starter project, not a production-hardened deployment. For public deployment, add individual user accounts, CSRF protection, rate limiting, and stronger secret management.


## New college-project features

### QR-based book issue and return
- In the Admin Dashboard, click **Book QR** beside a book to open its printable QR code.
- At the lending desk, start the camera scanner and scan the book QR. The book is selected in the issue form; enter the borrower and due date and submit to issue it.
- Each active loan has a **Return QR**. Open/print it and scan it with the camera scanner to record the return.
- If camera scanning is unavailable, enter the QR payload manually, such as `LIBTRACK:BOOK:1` or `LIBTRACK:LOAN:1`.
- Camera scanning requires a browser that supports `BarcodeDetector` (recent Chrome/Edge) and camera permission.

### Usage analytics dashboard
- Monthly borrowing trend, book count by category, and most borrowed books are shown on the Admin Dashboard.
- Charts are drawn in the browser from live MySQL query results. Use **Print dashboard** to save a print/PDF report.

### Install the new QR dependency
Run `python -m pip install -r requirements.txt` again after extracting the updated ZIP.


## Updated admin dashboard features
- **Book management:** add, edit, delete, search inventory, track physical copies, damaged/missing copies, and import a CSV file.
- **Borrower management:** borrowers are created during book issue; admins can suspend/reactivate them and change their borrowing limit. Suspended borrowers cannot be issued a book.
- **Circulation:** issue, return, renew for seven days, approve/reject reservations, and use book/loan QR codes. Reservation requests can be submitted from the public catalogue when a book has no available copies.
- **Reports and analytics:** daily, weekly and monthly circulation totals; most active readers; rarely borrowed books; monthly/category/popularity charts; CSV and PDF downloads. PDF export uses ReportLab, installed by `requirements.txt`.
- **Premium UI:** responsive layout, searchable inventory, edit panels, clear status badges, and a dark/light theme toggle whose choice is saved in the browser.

## CSV import format
Use a UTF-8 CSV file with headers: `title,author,isbn,category,total_copies`. Title and author are required. Leave ISBN blank if not available.
