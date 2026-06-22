-- students.sql
USE blog_db;
CREATE TABLE IF NOT EXISTS students
(
    id         INT PRIMARY KEY AUTO_INCREMENT COMMENT '文章ID',
    title      VARCHAR(255) NOT NULL COMMENT '文章标题',
    content    TEXT NOT NULL COMMENT '文章内容',
    slug       VARCHAR(100) UNIQUE NOT NULL COMMENT 'URL友好标识',
    author_id  VARCHAR(50) NOT NULL COMMENT '作者ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    status     ENUM ('draft', 'published') DEFAULT 'draft' COMMENT '状态：草稿/已发布',

    INDEX idx_slug (slug) COMMENT 'slug查询索引',
    INDEX idx_author (author_id) COMMENT '作者查询索引',
    INDEX idx_status (status) COMMENT '状态查询索引',
    INDEX idx_created_at (created_at) COMMENT '时间排序索引'
);