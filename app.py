import os
import hashlib
import uuid
from datetime import datetime
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify, send_from_directory, abort)
from werkzeug.utils import secure_filename
from config import Config
from database import db
from models.user import User
from models.report_gen import generate_pdf_report, generate_csv_report
from plagiarism_engine import analyze_plagiarism
from plagiarism_engine.tokenizer import detect_language

app = Flask(__name__)
app.config.from_object(Config)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['REPORTS_FOLDER'], exist_ok=True)


# ── Helpers ───────────────────────────────────────────────────
def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def faculty_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('role') not in ('faculty', 'admin'):
            flash('Faculty or Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


def current_user():
    if 'user_id' in session:
        return db.get_user_by_id(session['user_id'])
    return None


def file_hash(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()


# ── Auth routes ───────────────────────────────────────────────
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        user = db.get_user_by_email(email)
        if user and User.check_password(password, user['password']):
            if not user['is_active']:
                flash('Your account has been deactivated. Contact admin.', 'danger')
                return render_template('login.html')
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['email'] = user['email']
            session['role'] = user['role']
            session.permanent = True
            db.update_last_login(user['id'])
            flash(f"Welcome back, {user['name']}!", 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        role = request.form.get('role', 'student')

        if not all([name, email, password, confirm]):
            flash('All fields are required.', 'danger')
            return render_template('register.html')
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('register.html')
        if db.get_user_by_email(email):
            flash('Email already registered.', 'danger')
            return render_template('register.html')

        hashed = User.hash_password(password)
        db.create_user(name, email, hashed, role)
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ── Dashboard ─────────────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    stats = db.get_dashboard_stats()
    dist = db.get_similarity_distribution()
    recent = db.get_recent_comparisons(5)
    trend = db.get_monthly_trend()
    top_uploaders = db.get_top_uploaders(5)

    if session['role'] == 'student':
        uploads = db.get_uploads_by_user(session['user_id'])
        comparisons = db.get_comparisons_by_user(session['user_id'])
        stats['total_uploads'] = len(uploads)
        stats['total_comparisons'] = len(comparisons)
    else:
        comparisons = db.get_all_comparisons()

    user = current_user()
    return render_template('dashboard.html',
                           stats=stats, dist=dist, recent=recent,
                           trend=trend, top_uploaders=top_uploaders,
                           user=user)


# ── Upload routes ─────────────────────────────────────────────
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    user = current_user()
    if request.method == 'POST':
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            flash('No files selected.', 'danger')
            return redirect(request.url)

        uploaded = []
        errors = []
        for file in files:
            if file.filename == '':
                continue
            if not allowed_file(file.filename):
                errors.append(f"{file.filename}: Invalid file type.")
                continue

            orig_name = secure_filename(file.filename)
            unique_name = f"{uuid.uuid4().hex}_{orig_name}"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
            file.save(save_path)

            size = os.path.getsize(save_path)
            lang = detect_language(orig_name)
            fhash = file_hash(save_path)

            uid = db.create_upload(
                session['user_id'], unique_name, orig_name,
                size, lang, fhash
            )
            uploaded.append({'id': uid, 'name': orig_name})

        if uploaded:
            flash(f"{len(uploaded)} file(s) uploaded successfully.", 'success')
        for e in errors:
            flash(e, 'warning')
        return redirect(url_for('upload'))

    uploads = db.get_all_uploads() if session['role'] != 'student' \
        else db.get_uploads_by_user(session['user_id'])
    return render_template('upload.html', uploads=uploads, user=user)


@app.route('/upload/delete/<int:uid>', methods=['POST'])
@login_required
def delete_upload(uid):
    upload_row = db.get_upload_by_id(uid)
    if not upload_row:
        abort(404)
    if session['role'] == 'student' and upload_row['user_id'] != session['user_id']:
        abort(403)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], upload_row['filename'])
    if os.path.exists(filepath):
        os.remove(filepath)
    db.delete_upload(uid)
    flash('File deleted.', 'success')
    return redirect(url_for('upload'))


# ── Compare routes ────────────────────────────────────────────
@app.route('/compare', methods=['GET', 'POST'])
@login_required
def compare():
    user = current_user()
    if session['role'] == 'student':
        uploads = db.get_uploads_by_user(session['user_id'])
    else:
        uploads = db.get_all_uploads()

    if request.method == 'POST':
        file1_id = request.form.get('file1_id', type=int)
        file2_id = request.form.get('file2_id', type=int)

        if not file1_id or not file2_id:
            flash('Please select two files to compare.', 'danger')
            return redirect(request.url)
        if file1_id == file2_id:
            flash('Please select two different files.', 'danger')
            return redirect(request.url)

        f1 = db.get_upload_by_id(file1_id)
        f2 = db.get_upload_by_id(file2_id)

        if not f1 or not f2:
            flash('One or more files not found.', 'danger')
            return redirect(request.url)

        try:
            with open(os.path.join(app.config['UPLOAD_FOLDER'], f1['filename']), 'r', errors='ignore') as fp:
                code1 = fp.read()
            with open(os.path.join(app.config['UPLOAD_FOLDER'], f2['filename']), 'r', errors='ignore') as fp:
                code2 = fp.read()
        except Exception as e:
            flash(f'Error reading files: {e}', 'danger')
            return redirect(request.url)

        language = f1.get('language', 'python')
        result = analyze_plagiarism(code1, code2, language)

        cid = db.create_comparison(
            file1_id, file2_id,
            result['final_score'],
            result['token_similarity'],
            result['ast_similarity'],
            result['structure_similarity'],
            result['logic_similarity'],
            result['plagiarism_level'],
            session['user_id']
        )

        session['last_comparison'] = {
            'id': cid,
            'result': {k: v for k, v in result.items()
                       if k not in ('matching_blocks', 'different_blocks', 'ast_matches')},
            'file1': f1['original_filename'],
            'file2': f2['original_filename'],
            'code1': code1,
            'code2': code2,
            'matching_blocks': result['matching_blocks'][:20],
            'different_blocks': result['different_blocks'][:20],
            'ast_matches': result['ast_matches'][:10],
        }

        return redirect(url_for('compare_result', cid=cid))

    return render_template('compare.html', uploads=uploads, user=user)


@app.route('/compare/result/<int:cid>')
@login_required
def compare_result(cid):
    user = current_user()
    comp = db.get_comparison_by_id(cid)
    if not comp:
        abort(404)

    last = session.get('last_comparison', {})
    code1 = last.get('code1', '')
    code2 = last.get('code2', '')
    matching_blocks = last.get('matching_blocks', [])
    different_blocks = last.get('different_blocks', [])
    ast_matches = last.get('ast_matches', [])

    # Build highlighted lines sets
    match_lines_a = set()
    match_lines_b = set()
    for blk in matching_blocks:
        match_lines_a.update(blk.get('lines_a', []))
        match_lines_b.update(blk.get('lines_b', []))

    return render_template('compare_result.html',
                           comp=comp, user=user,
                           code1=code1, code2=code2,
                           match_lines_a=match_lines_a,
                           match_lines_b=match_lines_b,
                           matching_blocks=matching_blocks,
                           different_blocks=different_blocks,
                           ast_matches=ast_matches)


# ── Batch comparison ──────────────────────────────────────────
@app.route('/compare/batch', methods=['GET', 'POST'])
@faculty_required
def batch_compare():
    user = current_user()
    uploads = db.get_all_uploads()
    results = []

    if request.method == 'POST':
        file_ids = request.form.getlist('file_ids', type=int)
        if len(file_ids) < 2:
            flash('Select at least 2 files for batch comparison.', 'danger')
            return redirect(request.url)
        if len(file_ids) > 10:
            flash('Maximum 10 files allowed for batch comparison.', 'warning')
            file_ids = file_ids[:10]

        files_data = {}
        for fid in file_ids:
            row = db.get_upload_by_id(fid)
            if row:
                try:
                    with open(os.path.join(app.config['UPLOAD_FOLDER'], row['filename']), 'r', errors='ignore') as fp:
                        files_data[fid] = {'meta': row, 'code': fp.read()}
                except:
                    pass

        ids = list(files_data.keys())
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                id1, id2 = ids[i], ids[j]
                d1, d2 = files_data[id1], files_data[id2]
                lang = d1['meta'].get('language', 'python')
                result = analyze_plagiarism(d1['code'], d2['code'], lang)

                cid = db.create_comparison(
                    id1, id2,
                    result['final_score'], result['token_similarity'],
                    result['ast_similarity'], result['structure_similarity'],
                    result['logic_similarity'], result['plagiarism_level'],
                    session['user_id']
                )
                results.append({
                    'cid': cid,
                    'file1': d1['meta']['original_filename'],
                    'file2': d2['meta']['original_filename'],
                    'score': result['final_score'],
                    'level': result['plagiarism_level'],
                    'level_label': result['level_label'],
                })

        flash(f'Batch comparison complete: {len(results)} pair(s) analysed.', 'success')

    return render_template('batch_compare.html', uploads=uploads,
                           results=results, user=user)


# ── Reports ───────────────────────────────────────────────────
@app.route('/reports')
@login_required
def reports():
    user = current_user()
    if session['role'] == 'student':
        comps = db.get_comparisons_by_user(session['user_id'])
    else:
        comps = db.get_all_comparisons()
    return render_template('reports.html', comparisons=comps, user=user)


@app.route('/reports/download/<int:cid>/<fmt>')
@login_required
def download_report(cid, fmt):
    comp = db.get_comparison_by_id(cid)
    if not comp:
        abort(404)

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    last = session.get('last_comparison', {})
    result_data = last if last.get('id') == cid else {}

    if fmt == 'pdf':
        fname = f"report_{cid}_{ts}.pdf"
        generate_pdf_report(comp, result_data, fname)
        return send_from_directory(app.config['REPORTS_FOLDER'], fname,
                                   as_attachment=True)
    elif fmt == 'csv':
        fname = f"report_{cid}_{ts}.csv"
        generate_csv_report(comp, fname)
        return send_from_directory(app.config['REPORTS_FOLDER'], fname,
                                   as_attachment=True)
    abort(400)


# ── Analytics ─────────────────────────────────────────────────
@app.route('/analytics')
@faculty_required
def analytics():
    user = current_user()
    stats = db.get_dashboard_stats()
    dist = db.get_similarity_distribution()
    trend = db.get_monthly_trend()
    top_uploaders = db.get_top_uploaders(10)
    all_comps = db.get_all_comparisons()

    high = [c for c in all_comps if c['plagiarism_level'] == 'high']
    return render_template('analytics.html', stats=stats, dist=dist,
                           trend=trend, top_uploaders=top_uploaders,
                           high_cases=high, user=user)


# ── Admin panel ───────────────────────────────────────────────
@app.route('/admin')
@admin_required
def admin_panel():
    user = current_user()
    users = db.get_all_users()
    stats = db.get_dashboard_stats()
    return render_template('admin.html', users=users, stats=stats, user=user)


@app.route('/admin/toggle/<int:uid>', methods=['POST'])
@admin_required
def toggle_user(uid):
    if uid == session['user_id']:
        flash("You cannot deactivate your own account.", 'danger')
        return redirect(url_for('admin_panel'))
    db.toggle_user_active(uid)
    flash('User status updated.', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/admin/delete/<int:uid>', methods=['POST'])
@admin_required
def delete_user_admin(uid):
    if uid == session['user_id']:
        flash("You cannot delete your own account.", 'danger')
        return redirect(url_for('admin_panel'))
    db.delete_user(uid)
    flash('User deleted.', 'success')
    return redirect(url_for('admin_panel'))


# ── Profile ───────────────────────────────────────────────────
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = current_user()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_profile':
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip()
            if not name or not email:
                flash('Name and email are required.', 'danger')
            else:
                existing = db.get_user_by_email(email)
                if existing and existing['id'] != session['user_id']:
                    flash('Email already in use.', 'danger')
                else:
                    db.update_user_profile(session['user_id'], name, email)
                    session['name'] = name
                    session['email'] = email
                    flash('Profile updated successfully.', 'success')
                    return redirect(url_for('profile'))

        elif action == 'change_password':
            current_pw = request.form.get('current_password', '')
            new_pw = request.form.get('new_password', '')
            confirm_pw = request.form.get('confirm_password', '')
            if not User.check_password(current_pw, user['password']):
                flash('Current password is incorrect.', 'danger')
            elif new_pw != confirm_pw:
                flash('New passwords do not match.', 'danger')
            elif len(new_pw) < 6:
                flash('Password must be at least 6 characters.', 'danger')
            else:
                db.update_user_password(session['user_id'], User.hash_password(new_pw))
                flash('Password changed successfully.', 'success')
                return redirect(url_for('profile'))

    uploads = db.get_uploads_by_user(session['user_id'])
    comparisons = db.get_comparisons_by_user(session['user_id'])
    return render_template('profile.html', user=user,
                           uploads=uploads, comparisons=comparisons)


# ── API endpoints (JSON) ──────────────────────────────────────
@app.route('/api/stats')
@login_required
def api_stats():
    return jsonify(db.get_dashboard_stats())


@app.route('/api/uploads')
@login_required
def api_uploads():
    if session['role'] == 'student':
        data = db.get_uploads_by_user(session['user_id'])
    else:
        data = db.get_all_uploads()
    for row in data:
        if 'upload_date' in row:
            row['upload_date'] = str(row['upload_date'])
    return jsonify(data)


@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404,
                           msg='Page not found.'), 404


@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', code=403,
                           msg='Access denied.'), 403


@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', code=500,
                           msg='Internal server error.'), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
