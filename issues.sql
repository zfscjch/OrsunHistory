USE blog_db;

CREATE TABLE IF NOT EXISTS issues (
    id INT PRIMARY KEY AUTO_INCREMENT,
    upload_user VARCHAR(64) NOT NULL,
    error TEXT NOT NULL,
    upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_resolve BOOLEAN NOT NULL DEFAULT FALSE,
    is_broadcast BOOLEAN NOT NULL DEFAULT FALSE,
    INDEX idx_resolve (is_resolve),
    INDEX idx_time (upload_time)
);