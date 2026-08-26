-- MySQL dump 10.13 Distrib 8.0.44, for Win64 (x86_64)
-- Host: localhost    Database: blog_db
-- Server version 8.0.44
-- 导出时间: 2026-08-25 22:07:39

SET @OLD_CHARACTER_SET_CLIENT = @@CHARACTER_SET_CLIENT;
SET @OLD_CHARACTER_SET_RESULTS = @@CHARACTER_SET_RESULTS;
SET @OLD_COLLATION_CONNECTION = @@COLLATION_CONNECTION;
SET NAMES utf8mb4;
SET @OLD_TIME_ZONE = @@TIME_ZONE;
SET TIME_ZONE = '+00:00';
SET @OLD_UNIQUE_CHECKS = @@UNIQUE_CHECKS, UNIQUE_CHECKS = 0;
SET @OLD_FOREIGN_KEY_CHECKS = @@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS = 0;
SET @OLD_SQL_MODE = @@SQL_MODE, SQL_MODE = 'NO_AUTO_VALUE_ON_ZERO';
SET @OLD_SQL_NOTES = @@SQL_NOTES, SQL_NOTES = 0;

-- ============================================================
-- 表: articles (文章表)
-- ============================================================

DROP TABLE IF EXISTS `articles`;

CREATE TABLE `articles` (
                            `id` int NOT NULL AUTO_INCREMENT COMMENT '文章ID',
                            `title` varchar(255) NOT NULL COMMENT '文章标题',
                            `content` text NOT NULL COMMENT '文章内容',
                            `slug` varchar(100) NOT NULL COMMENT 'URL友好标识',
                            `author` varchar(50) DEFAULT NULL COMMENT '作者',
                            `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                            `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                            `status` enum('draft','published') DEFAULT 'draft' COMMENT '状态: draft=草稿, published=已发布',
                            `sayings` text COMMENT '名言/摘录',
                            PRIMARY KEY (`id`),
                            UNIQUE KEY `slug` (`slug`),
                            KEY `idx_slug` (`slug`) COMMENT 'slug索引',
                            KEY `idx_author` (`author`) COMMENT '作者索引',
                            KEY `idx_status` (`status`) COMMENT '状态索引',
                            KEY `idx_created_at` (`created_at`) COMMENT '创建时间索引'
) ENGINE = InnoDB AUTO_INCREMENT = 38 DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '文章表';

-- ============================================================
-- 表: comments (评论表)
-- ============================================================

DROP TABLE IF EXISTS `comments`;

CREATE TABLE `comments` (
                            `id` int NOT NULL AUTO_INCREMENT COMMENT '评论ID',
                            `article_id` int DEFAULT NULL COMMENT '所属文章ID（关联articles表）',
                            `student_id` int DEFAULT NULL COMMENT '所属学生文章ID（关联students表）',
                            `user_id` int DEFAULT NULL COMMENT '评论用户ID',
                            `parent_id` int DEFAULT NULL COMMENT '父评论ID',
                            `content` text NOT NULL COMMENT '评论内容',
                            `likes` int DEFAULT '0' COMMENT '点赞数',
                            `status` enum('pending','approved','spam','unrevealed') DEFAULT NULL COMMENT '状态: pending=待审核, approved=已通过, spam=垃圾, unrevealed=未显示',
                            `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '评论时间',
                            `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                            `anonymous` tinyint(1) DEFAULT '0' COMMENT '是否匿名: 0=否, 1=是',
                            PRIMARY KEY (`id`),
                            KEY `idx_article` (`article_id`),
                            KEY `idx_student` (`student_id`),
                            KEY `idx_user` (`user_id`),
                            KEY `idx_parent` (`parent_id`),
                            KEY `idx_status` (`status`),
                            KEY `idx_created` (`created_at`),
                            CONSTRAINT `fk_comments_article` FOREIGN KEY (`article_id`) REFERENCES `articles` (`id`) ON DELETE CASCADE,
                            CONSTRAINT `fk_comments_parent` FOREIGN KEY (`parent_id`) REFERENCES `comments` (`id`) ON DELETE CASCADE,
                            CONSTRAINT `fk_comments_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE,
                            CONSTRAINT `fk_comments_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE = InnoDB AUTO_INCREMENT = 9 DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '评论表';

-- ============================================================
-- 表: forum_boards (论坛版块表)
-- ============================================================

DROP TABLE IF EXISTS `forum_boards`;

CREATE TABLE `forum_boards` (
                                `id` int NOT NULL AUTO_INCREMENT COMMENT '版块ID',
                                `name` varchar(100) NOT NULL COMMENT '版块名称',
                                `description` text COMMENT '版块描述',
                                `icon` varchar(50) DEFAULT '📄' COMMENT '版块图标',
                                `sort_order` int DEFAULT '0' COMMENT '排序权重',
                                `is_active` tinyint(1) DEFAULT '1' COMMENT '是否启用: 1=启用, 0=禁用',
                                `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                                `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                                PRIMARY KEY (`id`)
) ENGINE = InnoDB AUTO_INCREMENT = 8 DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '论坛版块表';

-- ============================================================
-- 表: forum_likes (论坛点赞表)
-- ============================================================

DROP TABLE IF EXISTS `forum_likes`;

CREATE TABLE `forum_likes` (
                               `id` int NOT NULL AUTO_INCREMENT COMMENT '点赞记录ID',
                               `reply_id` int DEFAULT NULL COMMENT '被点赞的回复ID',
                               `thread_id` int DEFAULT NULL COMMENT '被点赞的主题ID',
                               `user_id` int NOT NULL COMMENT '点赞用户ID',
                               `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '点赞时间',
                               PRIMARY KEY (`id`),
                               KEY `reply_id` (`reply_id`),
                               KEY `thread_id` (`thread_id`),
                               CONSTRAINT `forum_likes_ibfk_1` FOREIGN KEY (`reply_id`) REFERENCES `forum_replies` (`id`),
                               CONSTRAINT `forum_likes_ibfk_2` FOREIGN KEY (`thread_id`) REFERENCES `forum_threads` (`id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '论坛点赞表';

-- ============================================================
-- 表: forum_replies (论坛回复表)
-- ============================================================

DROP TABLE IF EXISTS `forum_replies`;

CREATE TABLE `forum_replies` (
                                 `id` int NOT NULL AUTO_INCREMENT COMMENT '回复ID',
                                 `thread_id` int NOT NULL COMMENT '所属主题ID',
                                 `content` text NOT NULL COMMENT '回复内容',
                                 `author_id` int NOT NULL COMMENT '作者用户ID',
                                 `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                                 `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                                 `is_deleted` tinyint(1) DEFAULT '0' COMMENT '是否已删除: 0=否, 1=是',
                                 `is_anonymous` tinyint(1) DEFAULT '0' COMMENT '是否匿名: 0=否, 1=是',
                                 PRIMARY KEY (`id`),
                                 KEY `thread_id` (`thread_id`),
                                 CONSTRAINT `forum_replies_ibfk_1` FOREIGN KEY (`thread_id`) REFERENCES `forum_threads` (`id`)
) ENGINE = InnoDB AUTO_INCREMENT = 6 DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '论坛回复表';

-- ============================================================
-- 表: forum_threads (论坛主题表)
-- ============================================================

DROP TABLE IF EXISTS `forum_threads`;

CREATE TABLE `forum_threads` (
                                 `id` int NOT NULL AUTO_INCREMENT COMMENT '主题ID',
                                 `board_id` int NOT NULL COMMENT '所属版块ID',
                                 `title` varchar(200) NOT NULL COMMENT '主题标题',
                                 `content` text NOT NULL COMMENT '主题内容',
                                 `author_id` int NOT NULL COMMENT '作者用户ID',
                                 `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                                 `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                                 `view_count` int DEFAULT '0' COMMENT '浏览量',
                                 `reply_count` int DEFAULT '0' COMMENT '回复数',
                                 `last_reply_id` int DEFAULT NULL COMMENT '最后回复ID',
                                 `last_reply_at` datetime DEFAULT NULL COMMENT '最后回复时间',
                                 `is_pinned` tinyint(1) DEFAULT '0' COMMENT '是否置顶: 0=否, 1=是',
                                 `is_locked` tinyint(1) DEFAULT '0' COMMENT '是否锁定: 0=否, 1=是（锁定后不可回复）',
                                 `is_deleted` tinyint(1) DEFAULT '0' COMMENT '是否已删除: 0=否, 1=是',
                                 `is_anonymous` tinyint(1) DEFAULT '0' COMMENT '是否匿名: 0=否, 1=是',
                                 PRIMARY KEY (`id`),
                                 KEY `board_id` (`board_id`),
                                 CONSTRAINT `forum_threads_ibfk_1` FOREIGN KEY (`board_id`) REFERENCES `forum_boards` (`id`)
) ENGINE = InnoDB AUTO_INCREMENT = 5 DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '论坛主题表';

-- ============================================================
-- 表: issues (问题反馈表)
-- ============================================================

DROP TABLE IF EXISTS `issues`;

CREATE TABLE `issues` (
                          `id` int NOT NULL AUTO_INCREMENT COMMENT '反馈ID',
                          `upload_user` varchar(64) NOT NULL COMMENT '提交用户',
                          `error` text NOT NULL COMMENT '错误/问题描述',
                          `upload_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '提交时间',
                          `is_resolve` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否已解决: 0=未解决, 1=已解决',
                          `is_broadcast` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否广播: 0=否, 1=是',
                          PRIMARY KEY (`id`),
                          KEY `idx_resolve` (`is_resolve`),
                          KEY `idx_time` (`upload_time`)
) ENGINE = InnoDB AUTO_INCREMENT = 3 DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '问题反馈表';

-- ============================================================
-- 表: students (学生文章表)
-- ============================================================

DROP TABLE IF EXISTS `students`;

CREATE TABLE `students` (
                            `id` int NOT NULL AUTO_INCREMENT COMMENT '学生文章ID',
                            `title` varchar(255) NOT NULL COMMENT '文章标题',
                            `content` text NOT NULL COMMENT '文章内容',
                            `slug` varchar(100) NOT NULL COMMENT 'URL友好标识',
                            `author` varchar(50) NOT NULL COMMENT '作者',
                            `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                            `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                            `status` enum('draft', 'published', 'rejected') DEFAULT NULL COMMENT '状态: draft=草稿, published=已发布, rejected=已驳回',
                            PRIMARY KEY (`id`),
                            UNIQUE KEY `slug` (`slug`),
                            KEY `idx_slug` (`slug`) COMMENT 'slug索引',
                            KEY `idx_author` (`author`) COMMENT '作者索引',
                            KEY `idx_status` (`status`) COMMENT '状态索引',
                            KEY `idx_created_at` (`created_at`) COMMENT '创建时间索引'
) ENGINE = InnoDB AUTO_INCREMENT = 49 DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '学生文章表';

-- ============================================================
-- 表: users (用户表)
-- ============================================================

DROP TABLE IF EXISTS `users`;

CREATE TABLE `users` (
                         `id` int NOT NULL AUTO_INCREMENT COMMENT '用户ID',
                         `username` text COMMENT '用户名',
                         `password_hash` text COMMENT '密码哈希值',
                         `created_at` text COMMENT '创建时间',
                         `login_attempts` int DEFAULT NULL COMMENT '登录尝试次数',
                         `account_locked` int DEFAULT NULL COMMENT '账户是否锁定: 0=未锁定, 1=已锁定',
                         `is_admin` tinyint(1) DEFAULT '0' COMMENT '是否管理员: 0=否, 1=是',
                         `linked_user` text COMMENT '关联用户',
                         `is_active` tinyint(1) NOT NULL COMMENT '是否激活: 0=未激活, 1=已激活',
                         `settings` json DEFAULT NULL COMMENT '用户设置（JSON格式）',
                         PRIMARY KEY (`id`)
) ENGINE = InnoDB AUTO_INCREMENT = 70 DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '用户表';

-- ============================================================
-- 恢复原始设置
-- ============================================================

SET TIME_ZONE = @OLD_TIME_ZONE;
SET SQL_MODE = @OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS = @OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS = @OLD_UNIQUE_CHECKS;
SET CHARACTER_SET_CLIENT = @OLD_CHARACTER_SET_CLIENT;
SET CHARACTER_SET_RESULTS = @OLD_CHARACTER_SET_RESULTS;
SET COLLATION_CONNECTION = @OLD_COLLATION_CONNECTION;
SET SQL_NOTES = @OLD_SQL_NOTES;

-- Dump completed on 2026-08-25 22:07:39