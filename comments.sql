-- comments.sql
CREATE TABLE IF NOT EXISTS comments (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '评论ID',
    article_id INT DEFAULT NULL COMMENT '所属文章ID（关联articles表）',
    student_id INT DEFAULT NULL COMMENT '所属学生文章ID（关联students表）',
    user_id INT COMMENT '评论用户ID（如果是注册用户）',
    parent_id INT DEFAULT NULL COMMENT '父评论ID，用于回复功能',
    content TEXT NOT NULL COMMENT '评论内容',
    likes INT DEFAULT 0 COMMENT '点赞数',
    status ENUM('pending', 'approved', 'spam') DEFAULT 'approved' COMMENT '评论状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '评论时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    -- 外键约束
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (parent_id) REFERENCES comments(id) ON DELETE CASCADE,

    -- 约束：确保至少关联一个表
    CONSTRAINT chk_target CHECK (article_id IS NOT NULL OR student_id IS NOT NULL),

    -- 索引
    INDEX idx_article (article_id) COMMENT '文章查询索引',
    INDEX idx_student (student_id) COMMENT '学生文章查询索引',
    INDEX idx_user (user_id) COMMENT '用户查询索引',
    INDEX idx_article_created (article_id, created_at) COMMENT '文章评论排序',
    INDEX idx_student_created (student_id, created_at) COMMENT '学生文章评论排序',
    INDEX idx_status (status) COMMENT '状态查询'
) COMMENT='评论表';