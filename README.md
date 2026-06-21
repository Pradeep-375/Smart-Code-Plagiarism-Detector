# Smart Code Plagiarism Detector

> An intelligent, full-stack plagiarism detection system for source code submissions — built as a B.Tech Final Year Major Project.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Flask](https://img.shields.io/badge/Flask-3.0-green)
![MySQL](https://img.shields.io/badge/MySQL-8.0-orange)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple)

---

## 📋 Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Detection Algorithms](#detection-algorithms)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [User Roles](#user-roles)
- [Usage Guide](#usage-guide)
- [API Endpoints](#api-endpoints)
- [Demo Credentials](#demo-credentials)
- [Deployment](#deployment)

---

## ✨ Features

| Feature | Description |
|---|---|
| Multi-Algorithm Detection | Token matching, AST analysis, structural and logic similarity |
| Side-by-Side Comparison | Highlighted matching lines in a dark-themed code viewer |
| Batch Comparison | Compare entire assignment batches (N×(N-1)/2 pairs) |
| PDF & CSV Reports | Professional, downloadable reports with algorithm breakdown |
| Analytics Dashboard | Charts, trend graphs, top-uploader leaderboard |
| Role-Based Access | Student / Faculty / Admin with separate views |
| Dark / Light Theme | Persisted via localStorage |
| Language Support | Python, Java, C, C++ |

---

## 🛠 Tech Stack

**Backend:** Python 3.10+, Flask 3.0, PyMySQL, bcrypt, scikit-learn, Pygments, ReportLab  
**Frontend:** Bootstrap 5.3, Chart.js 4, Bootstrap Icons, Inter + JetBrains Mono fonts  
**Database:** MySQL 8.0  

---

## 🔬 Detection Algorithms

```
Final Score = Token(30%) + AST(30%) + Structure(20%) + Logic(20%)
```

| Algorithm | Weight | Method |
|---|---|---|
| Token Matching | 30% | Pygments tokenization + SequenceMatcher |
| AST Similarity | 30% | Python `ast` module / regex for C/Java |
| Structural Similarity | 20% | Count-based comparison of loops, functions, classes |
| Logic / Cosine Similarity | 20% | TF-IDF cosine + n-gram Jaccard average |

**Risk Levels:**
- 🟢 **0–30%** — Low Similarity (likely original)
- 🟡 **31–60%** — Medium Similarity (review advised)
- 🔴 **61–100%** — High Similarity (probable plagiarism)

---

## 📁 Project Structure

```
Smart-Code-Plagiarism-Detector/
├── app.py                    # Main Flask application & all routes
├── config.py                 # Environment configuration
├── requirements.txt
│
├── database/
│   ├── __init__.py           # Re-exports all DB helpers
│   ├── db.py                 # PyMySQL query helpers
│   └── schema.sql            # MySQL DDL + demo seed data
│
├── models/
│   ├── __init__.py
│   ├── user.py               # User model + bcrypt helpers
│   ├── comparison.py         # Upload & Comparison models
│   └── report_gen.py         # PDF & CSV report generation
│
├── plagiarism_engine/
│   ├── __init__.py           # analyze_plagiarism() entry point
│   ├── tokenizer.py          # Preprocessing, comment removal, tokenization
│   ├── ast_compare.py        # AST node extraction & comparison
│   ├── structure_similarity.py  # Structural feature comparison
│   └── logic_similarity.py   # Cosine, n-gram, token similarity
│
├── static/
│   ├── css/style.css         # Full design system (dark/light variables)
│   └── js/main.js            # Sidebar, charts, drag-drop, counters
│
├── templates/
│   ├── base.html             # Layout with sidebar, topbar, flash messages
│   ├── index.html            # Public landing page
│   ├── login.html            # Login with demo credential helper
│   ├── register.html         # Register with password strength meter
│   ├── dashboard.html        # Stats, charts, quick actions
│   ├── upload.html           # Drag-and-drop file uploader
│   ├── compare.html          # File selector for comparison
│   ├── compare_result.html   # Full result: gauge, breakdown, code viewer
│   ├── batch_compare.html    # Batch file selection and results
│   ├── reports.html          # Filterable reports table
│   ├── analytics.html        # Faculty/Admin analytics
│   ├── admin.html            # User management panel
│   ├── profile.html          # Profile editing and activity
│   └── error.html            # 403 / 404 / 500 pages
│
├── uploads/                  # Stored uploaded code files
└── reports/                  # Generated PDF/CSV reports
```

---

## 🚀 Installation

### 1. Clone / download the project

```bash
git clone https://github.com/yourname/smart-plagiarism-detector.git
cd smart-plagiarism-detector
```

### 2. Create a virtual environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up MySQL

```bash
mysql -u root -p < database/schema.sql
```

Or manually:
```sql
CREATE DATABASE plagiarism_detector;
USE plagiarism_detector;
SOURCE database/schema.sql;
```

### 5. Configure environment (optional)

Create a `.env` file or export environment variables:

```env
SECRET_KEY=your-secret-key-here
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=yourpassword
DB_NAME=plagiarism_detector
```

### 6. Run the application

```bash
python app.py
```

Open your browser at **http://localhost:5000**

---

## ⚙️ Configuration

Edit `config.py` to change:

| Setting | Default | Description |
|---|---|---|
| `SECRET_KEY` | auto-generated | Flask session secret |
| `DB_HOST` | `localhost` | MySQL host |
| `DB_USER` | `root` | MySQL user |
| `DB_PASSWORD` | `""` | MySQL password |
| `DB_NAME` | `plagiarism_detector` | Database name |
| `MAX_CONTENT_LENGTH` | `5 MB` | Max upload file size |
| `ALLOWED_EXTENSIONS` | `py,java,c,cpp` | Accepted file types |

---

## 👥 User Roles

| Role | Capabilities |
|---|---|
| **Student** | Upload files, compare own files, view/download own reports |
| **Faculty** | All student features + view all files, batch compare, analytics |
| **Admin** | All faculty features + user management panel |

---

## 📖 Usage Guide

### Uploading Files
1. Navigate to **Upload Code** in the sidebar
2. Drag and drop `.py`, `.java`, `.c`, or `.cpp` files (or click to browse)
3. Multiple files can be uploaded simultaneously (max 5 MB each)

### Comparing Two Files
1. Navigate to **Compare Files**
2. Select **File A** and **File B** from your uploaded files
3. Click **Analyze Plagiarism** — results appear in seconds
4. The result page shows:
   - Overall similarity gauge
   - Per-algorithm breakdown with progress bars
   - Side-by-side code view with matching lines highlighted in green
   - Download PDF or CSV report

### Batch Comparison (Faculty/Admin)
1. Navigate to **Batch Compare**
2. Check all files to include (2–10 files)
3. Click **Run Batch Comparison**
4. Results are sorted by similarity score (highest first)

### Viewing Analytics (Faculty/Admin)
The **Analytics** page shows:
- Distribution pie chart (Low/Medium/High)
- Monthly comparison trend bar chart
- Top uploaders leaderboard
- All high-risk cases table

---

## 🔌 API Endpoints (JSON)

| Endpoint | Auth | Description |
|---|---|---|
| `GET /api/stats` | Any | Dashboard statistics |
| `GET /api/uploads` | Any | List of accessible uploads |

---

## 🔑 Demo Credentials

All demo accounts use password: **`admin123`**

| Role | Email |
|---|---|
| Admin | admin@plagiarism.edu |
| Faculty | faculty@plagiarism.edu |
| Student | student@plagiarism.edu |

You can click any demo email on the login page to auto-fill credentials.

---

## 🌐 Deployment (Production)

### Using Gunicorn + Nginx

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

**Nginx config:**
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static/ {
        alias /path/to/Smart-Code-Plagiarism-Detector/static/;
    }

    client_max_body_size 10M;
}
```

### Environment checklist for production
- [ ] Set a strong `SECRET_KEY`
- [ ] Use a dedicated MySQL user (not root)
- [ ] Set `DEBUG = False` in config
- [ ] Configure HTTPS via Let's Encrypt
- [ ] Set `MAX_CONTENT_LENGTH` appropriately

---

## 📄 License

This project is developed as a B.Tech Final Year Major Project.  
© 2024 — All rights reserved.
