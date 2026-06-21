# database package — exposes db helpers at package level
from .db import (
    get_connection, query_one, query_all, execute,
    get_user_by_email, get_user_by_id, create_user,
    update_last_login, get_all_users, toggle_user_active,
    delete_user, update_user_profile, update_user_password,
    create_upload, get_upload_by_id, get_uploads_by_user,
    get_all_uploads, delete_upload,
    create_comparison, update_comparison_report,
    get_comparison_by_id, get_all_comparisons,
    get_comparisons_by_user,
    get_dashboard_stats, get_similarity_distribution,
    get_recent_comparisons, get_monthly_trend, get_top_uploaders,
)
