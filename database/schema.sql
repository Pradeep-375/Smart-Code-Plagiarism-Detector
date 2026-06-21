-- Smart Code Plagiarism Detector - Database Schema
-- MySQL Database

CREATE DATABASE IF NOT EXISTS plagiarism_detector;
USE plagiarism_detector;

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role ENUM('student', 'faculty', 'admin') DEFAULT 'student',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT TRUE
);

-- Uploads Table
CREATE TABLE IF NOT EXISTS uploads (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_size INT NOT NULL,
    language VARCHAR(50),
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_hash VARCHAR(64),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Comparisons Table
CREATE TABLE IF NOT EXISTS comparisons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    file1_id INT NOT NULL,
    file2_id INT NOT NULL,
    similarity_score DECIMAL(5,2) DEFAULT 0,
    token_similarity DECIMAL(5,2) DEFAULT 0,
    ast_similarity DECIMAL(5,2) DEFAULT 0,
    structure_similarity DECIMAL(5,2) DEFAULT 0,
    logic_similarity DECIMAL(5,2) DEFAULT 0,
    plagiarism_level ENUM('low', 'medium', 'high') DEFAULT 'low',
    compared_by INT,
    comparison_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    report_path VARCHAR(255),
    FOREIGN KEY (file1_id) REFERENCES uploads(id) ON DELETE CASCADE,
    FOREIGN KEY (file2_id) REFERENCES uploads(id) ON DELETE CASCADE,
    FOREIGN KEY (compared_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Reports Table
CREATE TABLE IF NOT EXISTS reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    comparison_id INT NOT NULL,
    generated_by INT,
    generated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    report_type ENUM('pdf', 'csv', 'html') DEFAULT 'pdf',
    report_path VARCHAR(255),
    FOREIGN KEY (comparison_id) REFERENCES comparisons(id) ON DELETE CASCADE,
    FOREIGN KEY (generated_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Insert default admin user (password: admin123)
INSERT INTO users (name, email, password, role) VALUES
('Admin User', 'admin@plagiarism.edu', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6oK0C5F8ji', 'admin'),
('Dr. Smith Faculty', 'faculty@plagiarism.edu', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6oK0C5F8ji', 'faculty'),
('John Student', 'student@plagiarism.edu', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6oK0C5F8ji', 'student');
