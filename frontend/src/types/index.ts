export type Role = 'admin' | 'faculty' | 'student'
export type Risk = 'low' | 'medium' | 'high'
export type ReviewStatus = 'pending' | 'dismissed' | 'flagged' | 'confirmed'

export interface User { id: number; email: string; full_name: string; role_name: Role; is_active: boolean; organization_id?: string | null; email_notifications: boolean; created_at: string; last_login_at?: string | null }
export interface Page<T> { items: T[]; total: number; page: number; page_size: number; unread?: number }
export interface Assignment { id: number; title: string; description: string; language_key: string; deadline: string | null; is_group: boolean; is_published: boolean; created_by: number; review_threshold: number | null; high_threshold: number | null; show_results_to_students: boolean; created_at: string; submission_count: number; my_submission_count?: number | null }
export interface SubmissionFile { id: number; filename: string; size_bytes: number; sha256: string; language_key: string }
export interface Submission { id: number; assignment_id: number; assignment_title?: string; student_id: number; student_name?: string; student_email?: string; group_id: number | null; version: number; status: string; submitted_at: string; is_late: boolean; duplicate_of_id: number | null; max_similarity: number | null; files: SubmissionFile[] }
export interface Job { id: number; assignment_id: number; status: 'queued' | 'running' | 'completed' | 'failed'; progress: number; total_pairs: number; done_pairs: number; error: string | null; include_history: boolean; created_at: string; started_at: string | null; finished_at: string | null }
export interface ResultSummary { id: number; assignment_id: number; assignment_title?: string; submission_a_id: number; submission_b_id: number; student_a: string; student_b: string; overall: number; effective_score: number; risk_level: Risk; confidence_label: string; is_duplicate: boolean; review_status: ReviewStatus; job_id: number }
export interface Segment { id: number; a_file: string; b_file: string; a_start_line: number; a_end_line: number; b_start_line: number; b_end_line: number; token_count: number }
export interface FileContent { id: number; filename: string; language_key: string; content: string }
export interface ResultDetail extends ResultSummary { scores: Record<string, number>; confidence: number; explanations: string[]; ml_probability: number | null; review_notes: string; override_score: number | null; reviewed_at: string | null; reviewer_name?: string | null; segments: Segment[]; files_a: FileContent[]; files_b: FileContent[]; disclaimer: string }
export interface Notification { id: number; title: string; message: string; link: string | null; is_read: boolean; created_at: string }
export interface AuditLog { id: number; user_id: number | null; user_email: string | null; action: string; entity_type: string | null; entity_id: number | null; ip_address: string | null; details: Record<string, unknown>; created_at: string }
export interface Language { id: number; key: string; name: string; extensions: string; enabled: boolean }
export interface Group { id: number; name: string; members: User[] }
export interface Feedback { submission_id: number; status: string; results_visible: boolean; max_similarity?: number | null; band?: 'low' | 'review' | 'high' | null; message: string }
export interface StaffDashboard {
  totals: { assignments: number; submissions: number; completed_analyses: number; pending_analyses: number; unanalyzed_submissions: number; average_similarity: number; high_similarity_cases: number; users?: number }
  language_distribution: { language: string; count: number }[]
  monthly_submissions: { month: string; count: number }[]
  assignment_stats: { assignment_id: number; title: string; language: string; submissions: number; pairs: number; average_similarity: number; flagged: number }[]
  cases_for_review: ResultSummary[]
  users_by_role?: { role: string; count: number }[]
}
export interface StudentDashboard {
  totals: { submissions: number; assignments_to_do: number; late_submissions: number; analyzed: number; pending: number }
  status_distribution: { status: string; count: number }[]
  todo: { id: number; title: string; language_key: string; deadline: string | null; overdue: boolean }[]
  recent: { id: number; assignment_id: number; assignment_title: string; version: number; status: string; submitted_at: string; is_late: boolean }[]
}
export interface DetectionSettings { weights: Record<string, number>; review_threshold: number; high_threshold: number; algorithms: string[] }
