import pymysql
import pymysql.cursors
from config import Config


def get_connection():
    return pymysql.connect(
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )


def query_one(sql, params=None):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchone()
    finally:
        conn.close()


def query_all(sql, params=None):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
    finally:
        conn.close()


def execute(sql, params=None):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.lastrowid
    finally:
        conn.close()


# ── User queries ──────────────────────────────────────────────
def get_user_by_email(email):
    return query_one("SELECT * FROM users WHERE email=%s", (email,))


def get_user_by_id(uid):
    return query_one("SELECT * FROM users WHERE id=%s", (uid,))


def create_user(name, email, hashed_pw, role='student'):
    return execute(
        "INSERT INTO users (name,email,password,role) VALUES (%s,%s,%s,%s)",
        (name, email, hashed_pw, role)
    )


def update_last_login(uid):
    execute("UPDATE users SET last_login=NOW() WHERE id=%s", (uid,))


def get_all_users():
    return query_all("SELECT id,name,email,role,created_at,last_login,is_active FROM users ORDER BY created_at DESC")


def toggle_user_active(uid):
    execute("UPDATE users SET is_active = NOT is_active WHERE id=%s", (uid,))


def delete_user(uid):
    execute("DELETE FROM users WHERE id=%s", (uid,))


def update_user_profile(uid, name, email):
    execute("UPDATE users SET name=%s, email=%s WHERE id=%s", (name, email, uid))


def update_user_password(uid, hashed_pw):
    execute("UPDATE users SET password=%s WHERE id=%s", (hashed_pw, uid))


# ── Upload queries ────────────────────────────────────────────
def create_upload(user_id, filename, original_filename, file_size, language, file_hash):
    return execute(
        "INSERT INTO uploads (user_id,filename,original_filename,file_size,language,file_hash) "
        "VALUES (%s,%s,%s,%s,%s,%s)",
        (user_id, filename, original_filename, file_size, language, file_hash)
    )


def get_upload_by_id(uid):
    return query_one(
        "SELECT u.*,us.name as uploader_name FROM uploads u "
        "JOIN users us ON u.user_id=us.id WHERE u.id=%s", (uid,)
    )


def get_uploads_by_user(user_id):
    return query_all(
        "SELECT * FROM uploads WHERE user_id=%s ORDER BY upload_date DESC", (user_id,)
    )


def get_all_uploads():
    return query_all(
        "SELECT u.*,us.name as uploader_name FROM uploads u "
        "JOIN users us ON u.user_id=us.id ORDER BY u.upload_date DESC"
    )


def delete_upload(uid):
    execute("DELETE FROM uploads WHERE id=%s", (uid,))


# ── Comparison queries ────────────────────────────────────────
def create_comparison(file1_id, file2_id, similarity_score, token_sim,
                      ast_sim, struct_sim, logic_sim, level, compared_by):
    return execute(
        "INSERT INTO comparisons (file1_id,file2_id,similarity_score,token_similarity,"
        "ast_similarity,structure_similarity,logic_similarity,plagiarism_level,compared_by) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (file1_id, file2_id, similarity_score, token_sim, ast_sim, struct_sim,
         logic_sim, level, compared_by)
    )


def update_comparison_report(cid, report_path):
    execute("UPDATE comparisons SET report_path=%s WHERE id=%s", (report_path, cid))


def get_comparison_by_id(cid):
    return query_one(
        "SELECT c.*, "
        "u1.original_filename as file1_name, u1.language as file1_lang, "
        "u2.original_filename as file2_name, u2.language as file2_lang, "
        "us.name as compared_by_name "
        "FROM comparisons c "
        "JOIN uploads u1 ON c.file1_id=u1.id "
        "JOIN uploads u2 ON c.file2_id=u2.id "
        "LEFT JOIN users us ON c.compared_by=us.id "
        "WHERE c.id=%s", (cid,)
    )


def get_all_comparisons():
    return query_all(
        "SELECT c.*, "
        "u1.original_filename as file1_name, "
        "u2.original_filename as file2_name, "
        "us.name as compared_by_name "
        "FROM comparisons c "
        "JOIN uploads u1 ON c.file1_id=u1.id "
        "JOIN uploads u2 ON c.file2_id=u2.id "
        "LEFT JOIN users us ON c.compared_by=us.id "
        "ORDER BY c.comparison_date DESC"
    )


def get_comparisons_by_user(user_id):
    return query_all(
        "SELECT c.*, "
        "u1.original_filename as file1_name, "
        "u2.original_filename as file2_name "
        "FROM comparisons c "
        "JOIN uploads u1 ON c.file1_id=u1.id "
        "JOIN uploads u2 ON c.file2_id=u2.id "
        "WHERE c.compared_by=%s "
        "ORDER BY c.comparison_date DESC", (user_id,)
    )


# ── Dashboard stats ───────────────────────────────────────────
def get_dashboard_stats():
    total_uploads = query_one("SELECT COUNT(*) as cnt FROM uploads")['cnt']
    total_comparisons = query_one("SELECT COUNT(*) as cnt FROM comparisons")['cnt']
    avg_similarity = query_one("SELECT COALESCE(AVG(similarity_score),0) as avg FROM comparisons")['avg']
    high_cases = query_one("SELECT COUNT(*) as cnt FROM comparisons WHERE plagiarism_level='high'")['cnt']
    total_users = query_one("SELECT COUNT(*) as cnt FROM users")['cnt']
    return {
        'total_uploads': total_uploads,
        'total_comparisons': total_comparisons,
        'avg_similarity': round(float(avg_similarity), 2),
        'high_cases': high_cases,
        'total_users': total_users,
    }


def get_similarity_distribution():
    rows = query_all(
        "SELECT plagiarism_level, COUNT(*) as cnt FROM comparisons GROUP BY plagiarism_level"
    )
    dist = {'low': 0, 'medium': 0, 'high': 0}
    for r in rows:
        dist[r['plagiarism_level']] = r['cnt']
    return dist


def get_recent_comparisons(limit=5):
    return query_all(
        "SELECT c.id, c.similarity_score, c.plagiarism_level, c.comparison_date,"
        "u1.original_filename as file1_name, u2.original_filename as file2_name "
        "FROM comparisons c "
        "JOIN uploads u1 ON c.file1_id=u1.id "
        "JOIN uploads u2 ON c.file2_id=u2.id "
        "ORDER BY c.comparison_date DESC LIMIT %s", (limit,)
    )


def get_monthly_trend():
    return query_all(
        "SELECT DATE_FORMAT(comparison_date,'%%Y-%%m') as month, "
        "COUNT(*) as comparisons, AVG(similarity_score) as avg_score "
        "FROM comparisons "
        "GROUP BY month ORDER BY month DESC LIMIT 12"
    )


def get_top_uploaders(limit=5):
    return query_all(
        "SELECT u.name, COUNT(up.id) as upload_count "
        "FROM users u JOIN uploads up ON u.id=up.user_id "
        "GROUP BY u.id,u.name ORDER BY upload_count DESC LIMIT %s", (limit,)
    )
