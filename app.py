import os, csv, io
from datetime import date
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response, Response
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error
import qrcode

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'change-this-development-secret')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', '1234')

def get_db():
    return mysql.connector.connect(host=os.getenv('DB_HOST','localhost'), port=int(os.getenv('DB_PORT','3306')), user=os.getenv('DB_USER','root'), password=os.getenv('DB_PASSWORD',''), database=os.getenv('DB_NAME','library_analysis'))

def query(sql, params=(), fetch=True):
    conn = get_db(); cur = conn.cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        result = cur.fetchall() if fetch else None
        if not fetch: conn.commit()
        return result
    finally:
        cur.close(); conn.close()

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('is_admin'):
            flash('Please sign in to the admin dashboard.', 'warning')
            return redirect(url_for('admin_login'))
        return fn(*args, **kwargs)
    return wrapper

@app.route('/')
def index():
    search = request.args.get('q','').strip()
    try:
        if search:
            books = query('SELECT * FROM books WHERE title LIKE %s OR author LIKE %s OR isbn LIKE %s ORDER BY title', (f'%{search}%',f'%{search}%',f'%{search}%'))
        else: books = query('SELECT * FROM books ORDER BY title')
        loans = query("SELECT l.*, b.title FROM loans l JOIN books b ON b.id=l.book_id WHERE l.borrower_name=%s AND l.status='Issued' ORDER BY l.due_date", (request.args.get('borrower',''),)) if request.args.get('borrower') else []
        db_error = None
    except Error as e:
        books, loans, db_error = [], [], str(e)
    return render_template('index.html', books=books, search=search, loans=loans, db_error=db_error)


@app.route('/reserve', methods=['POST'])
def reserve_book():
    try:
        book_id=int(request.form['book_id']); name=request.form.get('borrower_name','').strip(); email=request.form.get('email','').strip()
        if not name: raise ValueError('Enter your name to request a reservation.')
        book=query('SELECT id,title FROM books WHERE id=%s',(book_id,))
        if not book: raise ValueError('Book not found.')
        query("INSERT INTO reservations(book_id,borrower_name,email,status) VALUES(%s,%s,%s,'Pending')",(book_id,name,email),fetch=False)
        flash('Reservation request sent to the librarian.','success')
    except (Error,ValueError,KeyError) as e: flash(f'Could not reserve book: {e}','danger')
    return redirect(url_for('index'))

@app.route('/my-loans', methods=['GET','POST'])
def my_loans():
    name = request.values.get('name','').strip()
    loans=[]; error=None
    if name:
        try: loans = query("SELECT l.*, b.title, b.author FROM loans l JOIN books b ON b.id=l.book_id WHERE l.borrower_name=%s ORDER BY l.issue_date DESC", (name,))
        except Error as e: error=str(e)
    return render_template('my_loans.html', name=name, loans=loans, db_error=error)

@app.route('/admin/login', methods=['POST'])
def admin_login():
    password = request.form.get('password','')
    if password == ADMIN_PASSWORD:
        session['is_admin'] = True
        flash('Welcome to the admin dashboard.', 'success')
        return redirect(url_for('admin_dashboard'))
    flash('Incorrect admin password. Please try again.', 'danger')
    return redirect(url_for('index'))

@app.route('/admin/logout')
def admin_logout():
    session.clear(); flash('You have been logged out.', 'info'); return redirect(url_for('index'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    try:
        books=query('SELECT * FROM books ORDER BY id DESC')
        stats=query("SELECT (SELECT COUNT(*) FROM books) book_count, (SELECT COUNT(*) FROM borrowers) borrower_count, (SELECT COUNT(*) FROM loans WHERE status='Issued') issued_count, (SELECT COUNT(*) FROM loans WHERE status='Issued' AND due_date<CURDATE()) overdue_count")[0]
        recent=query('SELECT l.*, b.title FROM loans l JOIN books b ON b.id=l.book_id ORDER BY l.id DESC LIMIT 8')
        borrowers=query('SELECT * FROM borrowers ORDER BY full_name')
        reservations=query('SELECT r.*, b.title FROM reservations r JOIN books b ON b.id=r.book_id ORDER BY r.created_at DESC LIMIT 30')
        low_stock=query('SELECT * FROM books WHERE available_copies<=1 ORDER BY available_copies,title LIMIT 8')
        monthly=query("SELECT DATE_FORMAT(issue_date,'%Y-%m') AS month, COUNT(*) AS total FROM loans WHERE issue_date >= DATE_SUB(CURDATE(), INTERVAL 5 MONTH) GROUP BY DATE_FORMAT(issue_date,'%Y-%m') ORDER BY month")
        categories=query('SELECT category, COUNT(*) AS total FROM books GROUP BY category ORDER BY total DESC LIMIT 8')
        popular=query("SELECT b.title, COUNT(l.id) AS total FROM books b LEFT JOIN loans l ON l.book_id=b.id GROUP BY b.id,b.title ORDER BY total DESC,b.title LIMIT 6")
        active_readers=query("SELECT borrower_name,COUNT(*) AS total FROM loans GROUP BY borrower_name ORDER BY total DESC,borrower_name LIMIT 5")
        rarely_borrowed=query("SELECT b.title,COUNT(l.id) AS total FROM books b LEFT JOIN loans l ON l.book_id=b.id GROUP BY b.id,b.title ORDER BY total ASC,b.title LIMIT 5")
        period_stats=query("SELECT SUM(issue_date=CURDATE()) AS today, SUM(issue_date>=DATE_SUB(CURDATE(),INTERVAL 7 DAY)) AS week, SUM(issue_date>=DATE_FORMAT(CURDATE(),'%Y-%m-01')) AS month FROM loans")[0]
        error=None
    except Error as e: books=[]; stats={}; recent=[]; borrowers=[]; reservations=[]; low_stock=[]; monthly=[]; categories=[]; popular=[]; active_readers=[]; rarely_borrowed=[]; period_stats={}; error=str(e)
    return render_template('admin.html', books=books, stats=stats, recent=recent, borrowers=borrowers, monthly=monthly, categories=categories, popular=popular, active_readers=active_readers if 'active_readers' in locals() else [], rarely_borrowed=rarely_borrowed if 'rarely_borrowed' in locals() else [], period_stats=period_stats if 'period_stats' in locals() else {}, reservations=reservations if 'reservations' in locals() else [], low_stock=low_stock if 'low_stock' in locals() else [], db_error=error)

@app.route('/admin/books/add', methods=['POST'])
@admin_required
def add_book():
    try:
        query('INSERT INTO books(title,author,isbn,category,total_copies,available_copies) VALUES(%s,%s,%s,%s,%s,%s)', (request.form['title'].strip(),request.form['author'].strip(),(request.form.get('isbn','').strip() or None),request.form.get('category','General').strip(),int(request.form.get('total_copies',1)),int(request.form.get('total_copies',1))), fetch=False)
        flash('Book added successfully.','success')
    except (Error, ValueError, KeyError) as e: flash(f'Could not add book: {e}','danger')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/books/<int:book_id>/delete', methods=['POST'])
@admin_required
def delete_book(book_id):
    try:
        query('DELETE FROM books WHERE id=%s',(book_id,),fetch=False); flash('Book deleted.','success')
    except Error as e: flash(f'Book cannot be deleted if it has loan history: {e}','danger')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/loans/issue', methods=['POST'])
@admin_required
def issue_book():
    try:
        book_id=int(request.form['book_id']); name=request.form['borrower_name'].strip(); email=request.form.get('email','').strip()
        due=request.form['due_date']
        if not name: raise ValueError('Borrower name is required.')
        rows=query('SELECT available_copies FROM books WHERE id=%s',(book_id,))
        if not rows or rows[0]['available_copies'] < 1: raise ValueError('This book is not available.')
        borrower=query('SELECT id FROM borrowers WHERE full_name=%s',(name,))
        if borrower:
            borrower_id=borrower[0]['id']
            profile=query('SELECT is_active,borrow_limit FROM borrowers WHERE id=%s',(borrower_id,))[0]
            if not profile['is_active']: raise ValueError('This borrower account is suspended.')
            active=query("SELECT COUNT(*) AS n FROM loans WHERE borrower_id=%s AND status='Issued'",(borrower_id,))[0]['n']
            if active >= profile['borrow_limit']: raise ValueError('This borrower has reached their borrowing limit.')
        else:
            query('INSERT INTO borrowers(full_name,email) VALUES(%s,%s)',(name,email),fetch=False)
            borrower_id=query('SELECT id FROM borrowers WHERE full_name=%s ORDER BY id DESC LIMIT 1',(name,))[0]['id']
        query("INSERT INTO loans(book_id,borrower_id,borrower_name,issue_date,due_date,status) VALUES(%s,%s,%s,CURDATE(),%s,'Issued')",(book_id,borrower_id,name,due),fetch=False)
        query('UPDATE books SET available_copies=available_copies-1 WHERE id=%s',(book_id,),fetch=False)
        flash('Book issued successfully.','success')
    except (Error, ValueError, KeyError) as e: flash(f'Could not issue book: {e}','danger')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/loans/<int:loan_id>/return', methods=['POST'])
@admin_required
def return_book(loan_id):
    try:
        rows=query("SELECT book_id FROM loans WHERE id=%s AND status='Issued'",(loan_id,))
        if not rows: raise ValueError('Loan was already returned or does not exist.')
        query("UPDATE loans SET status='Returned', return_date=CURDATE() WHERE id=%s",(loan_id,),fetch=False)
        query('UPDATE books SET available_copies=LEAST(total_copies,available_copies+1) WHERE id=%s',(rows[0]['book_id'],),fetch=False)
        flash('Book return recorded.','success')
    except (Error, ValueError) as e: flash(f'Could not return book: {e}','danger')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reports.csv')
@admin_required
def report_csv():
    rows=query('SELECT l.id, b.title, l.borrower_name, l.issue_date, l.due_date, l.return_date, l.status FROM loans l JOIN books b ON b.id=l.book_id ORDER BY l.id DESC')
    out=io.StringIO(); writer=csv.writer(out); writer.writerow(['Loan ID','Book','Borrower','Issue Date','Due Date','Return Date','Status'])
    for r in rows: writer.writerow([r.get('id'),r.get('title'),r.get('borrower_name'),r.get('issue_date'),r.get('due_date'),r.get('return_date'),r.get('status')])
    response=make_response('\ufeff'+out.getvalue()); response.headers['Content-Type']='text/csv; charset=utf-8'; response.headers['Content-Disposition']='attachment; filename=library-loan-report.csv'; return response


@app.route('/admin/qr/book/<int:book_id>')
@admin_required
def book_qr(book_id):
    rows=query('SELECT id,title FROM books WHERE id=%s',(book_id,))
    if not rows: return 'Book not found', 404
    img=qrcode.make(f"LIBTRACK:BOOK:{book_id}")
    output=io.BytesIO(); img.save(output, format='PNG')
    return Response(output.getvalue(), mimetype='image/png', headers={'Cache-Control':'no-store'})

@app.route('/admin/qr/loan/<int:loan_id>')
@admin_required
def loan_qr(loan_id):
    rows=query("SELECT id FROM loans WHERE id=%s AND status='Issued'",(loan_id,))
    if not rows: return 'Active loan not found', 404
    img=qrcode.make(f"LIBTRACK:LOAN:{loan_id}")
    output=io.BytesIO(); img.save(output, format='PNG')
    return Response(output.getvalue(), mimetype='image/png', headers={'Cache-Control':'no-store'})

@app.route('/admin/scan-action', methods=['POST'])
@admin_required
def scan_action():
    code=request.form.get('code','').strip()
    try:
        parts=code.split(':')
        if len(parts)!=3 or parts[0] != 'LIBTRACK': raise ValueError('This QR code is not from LibTrack.')
        kind=parts[1]; item_id=int(parts[2])
        if kind=='BOOK':
            rows=query('SELECT id,title,available_copies FROM books WHERE id=%s',(item_id,))
            if not rows: raise ValueError('Book not found.')
            if rows[0]['available_copies']<1: raise ValueError('This book is currently unavailable.')
            session['scanned_book_id']=item_id
            flash(f"Scanned book: {rows[0]['title']}. Select a borrower and submit the issue form.",'success')
        elif kind=='LOAN':
            rows=query("SELECT book_id FROM loans WHERE id=%s AND status='Issued'",(item_id,))
            if not rows: raise ValueError('Active loan not found or already returned.')
            query("UPDATE loans SET status='Returned', return_date=CURDATE() WHERE id=%s",(item_id,),fetch=False)
            query('UPDATE books SET available_copies=LEAST(total_copies,available_copies+1) WHERE id=%s',(rows[0]['book_id'],),fetch=False)
            flash('QR scanned: book return recorded successfully.','success')
        else: raise ValueError('Unknown LibTrack QR type.')
    except (Error, ValueError) as e: flash(f'QR action failed: {e}','danger')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/books/<int:book_id>/edit', methods=['POST'])
@admin_required
def edit_book(book_id):
    try:
        title=request.form['title'].strip(); author=request.form['author'].strip(); category=request.form.get('category','General').strip()
        total=max(0,int(request.form.get('total_copies',1))); damaged=max(0,int(request.form.get('damaged_copies',0))); missing=max(0,int(request.form.get('missing_copies',0)))
        old=query('SELECT total_copies,available_copies FROM books WHERE id=%s',(book_id,))
        if not old: raise ValueError('Book not found.')
        issued=old[0]['total_copies']-old[0]['available_copies']
        if total < issued: raise ValueError('Total copies cannot be less than currently issued copies.')
        if damaged+missing > total-issued: raise ValueError('Damaged and missing copies exceed copies not currently issued.')
        available=total-issued-damaged-missing
        query('UPDATE books SET title=%s,author=%s,isbn=%s,category=%s,total_copies=%s,available_copies=%s,damaged_copies=%s,missing_copies=%s,cover_url=%s WHERE id=%s',(title,author,request.form.get('isbn','').strip() or None,category,total,available,damaged,missing,request.form.get('cover_url','').strip(),book_id),fetch=False)
        flash('Book details updated.','success')
    except (Error,ValueError,KeyError) as e: flash(f'Could not update book: {e}','danger')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/borrowers/<int:borrower_id>/toggle', methods=['POST'])
@admin_required
def toggle_borrower(borrower_id):
    try:
        query('UPDATE borrowers SET is_active=1-is_active WHERE id=%s',(borrower_id,),fetch=False); flash('Borrower account status updated.','success')
    except Error as e: flash(f'Could not update borrower: {e}','danger')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/borrowers/<int:borrower_id>/limit', methods=['POST'])
@admin_required
def set_borrow_limit(borrower_id):
    try:
        limit=max(1,min(20,int(request.form.get('borrow_limit',3))))
        query('UPDATE borrowers SET borrow_limit=%s WHERE id=%s',(limit,borrower_id),fetch=False); flash('Borrowing limit updated.','success')
    except (Error,ValueError) as e: flash(f'Could not update limit: {e}','danger')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reservations/<int:reservation_id>/<action>', methods=['POST'])
@admin_required
def reservation_action(reservation_id, action):
    if action not in ('approve','reject'): return 'Invalid action', 400
    try:
        query("UPDATE reservations SET status=%s WHERE id=%s AND status='Pending'",('Approved' if action=='approve' else 'Rejected',reservation_id),fetch=False)
        flash('Reservation updated.','success')
    except Error as e: flash(f'Could not update reservation: {e}','danger')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/loans/<int:loan_id>/renew', methods=['POST'])
@admin_required
def renew_loan(loan_id):
    try:
        query("UPDATE loans SET due_date=DATE_ADD(GREATEST(due_date,CURDATE()), INTERVAL 7 DAY) WHERE id=%s AND status='Issued'",(loan_id,),fetch=False)
        flash('Loan renewed for 7 days.','success')
    except Error as e: flash(f'Could not renew loan: {e}','danger')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reports.pdf')
@admin_required
def report_pdf():
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        rows=query('SELECT l.id,b.title,l.borrower_name,l.issue_date,l.due_date,l.return_date,l.status FROM loans l JOIN books b ON b.id=l.book_id ORDER BY l.id DESC')
        out=io.BytesIO(); c=canvas.Canvas(out,pagesize=A4); width,height=A4; y=height-45
        c.setFont('Helvetica-Bold',16); c.drawString(40,y,'LibTrack - Library Loan Report'); y-=28
        c.setFont('Helvetica',8); c.drawString(40,y,'Loan | Book | Borrower | Issued | Due | Status'); y-=18
        for r in rows:
            line=f"{r['id']} | {r['title']} | {r['borrower_name']} | {r['issue_date']} | {r['due_date']} | {r['status']}"
            c.drawString(40,y,line[:125]); y-=14
            if y<45: c.showPage(); y=height-45; c.setFont('Helvetica',8)
        c.save(); out.seek(0); return Response(out.getvalue(),mimetype='application/pdf',headers={'Content-Disposition':'attachment; filename=library-loan-report.pdf'})
    except ImportError: flash('Install reportlab with pip install reportlab to export PDF reports.','warning'); return redirect(url_for('admin_dashboard'))

@app.route('/admin/books/import', methods=['POST'])
@admin_required
def import_books():
    file=request.files.get('file')
    if not file or not file.filename.lower().endswith('.csv'):
        flash('Choose a CSV file with title, author, isbn, category, total_copies columns.','warning'); return redirect(url_for('admin_dashboard'))
    try:
        reader=csv.DictReader(io.StringIO(file.stream.read().decode('utf-8-sig')))
        count=0
        for row in reader:
            title=(row.get('title') or '').strip(); author=(row.get('author') or '').strip()
            if not title or not author: continue
            total=max(1,int(row.get('total_copies') or 1))
            query('INSERT INTO books(title,author,isbn,category,total_copies,available_copies) VALUES(%s,%s,%s,%s,%s,%s)',(title,author,(row.get('isbn') or '').strip() or None,(row.get('category') or 'General').strip(),total,total),fetch=False); count+=1
        flash(f'Imported {count} book(s).','success')
    except (Error,ValueError,UnicodeDecodeError) as e: flash(f'CSV import failed: {e}','danger')
    return redirect(url_for('admin_dashboard'))

@app.route('/health')
def health():
    try: query('SELECT 1'); return {'status':'ok','database':'connected'}
    except Error as e: return {'status':'error','database':str(e)}, 503

if __name__ == '__main__':
    app.run(debug=True)
