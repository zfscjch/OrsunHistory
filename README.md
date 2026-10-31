# 翱三通史官网 OrsunHistory

> 记录奥山实验初级中学 2023 届 3 班初中生活的纪念性网站。

## 项目简介

**翱三通史**是为**奥山实验初级中学 2023 届 3 班**建立的班级历史记录网站。网站用于储存和展示本届的**教师传记**与**学生传记**，同时提供论坛、聊天、人脸识别登录等互动功能。

- **线上地址**：https://www.cjchcoderchat.site:3/
- **访问限制**：2026 年中考前（预计 6 月 22 日前）禁止教师访问，以保证学生内容的私密性。
- **开源协议**：MIT License。

## 功能特性

- **传记浏览与阅读**：教师传记、学生传记的文章阅读器与分享页。
- **文章编辑与审核**：作者可编辑文章，设有文章审核与管理员日志机制。
- **论坛系统**：论坛首页、板块、发帖、帖子详情及 404 论坛页。
- **实时聊天**：基于 Socket.IO 的聊天模块，含独立移动端页面。
- **人脸识别登录**：基于新版后台 `face_recognizer_new.py` 的人脸识别登录，配合用户身份验证与登录锁定（旧版 `face_recognizer.py` 已弃用）。
- **身份验证**：`secret.js` 配合 `avoid_titles.html` 及 `get_titles.py` 完成用户身份校验。
- **维护模式**：支持维护模式与 503 状态页。
- **错误申报**：用户可申报网站错误，管理员统一管理。

> **说明**：`chat.html` 前端页面包含在本项目中，但其依赖的后端服务 **CoderChat** 因团队原因未开源，敬请谅解。

## 技术栈

| 层面 | 技术 |
|---|---|
| 后端 | Python（Flask） |
| 数据库 | MySQL（结构见 `blog_db.sql`） |
| 前端 | HTML / CSS / JavaScript |
| 实时通信 | Socket.IO |
| Markdown 渲染 | marked.umd.js |
| 人脸识别 | 自研 Python 后台（`face_recognizer_new.py`；旧版 `face_recognizer.py` 已弃用） |

## 快速开始

### 1. 环境要求

- Python 3.8 及以上
- MySQL 5.7+ 或 8.0+
- Node.js（仅前端依赖需要，如 `package.json` 所定义）

### 2. 安装依赖

```bash
pip install -r requirements.txt
npm install
```

> `npm install` 仅用于获取/更新前端依赖（如 `socket.io.js`）。若仓库中已包含 `static/js/socket.io.js`，生产部署可跳过此步。

> 若 `requirements.txt` 未包含人脸识别相关依赖（如 `face_recognition`、`opencv-python`、`dlib`），请根据 `face_recognizer_new.py` 的导入另行安装。

### 3. 初始化数据库

将 `blog_db.sql` 导入 MySQL：

```bash
mysql -u <用户名> -p <数据库名> < blog_db.sql
```

### 4. 配置

复制 `functions/config.example.py` 为 `functions/config.py`。若仓库未提供示例文件，请按以下字段自行创建：

```python
# functions/config.py
DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "root"
DB_PASSWORD = "your_password"
DB_NAME = "orsun_history"
SECRET_KEY = "change-me"
```

> `functions/config.py` 已被 `.gitignore` 忽略，请勿将真实密码提交到仓库。

### 5. 运行

**开发环境**：

```bash
python orsun_server.py
```

**生产环境**：

```bash
python run.py
```

> 生产环境建议配合反向代理（如 Nginx）与进程管理工具使用。

> 聊天功能依赖外部 CoderChat 后端，部署时需自行提供，否则 `chat.html` 无法完整运行。

## 数据与安全说明

> **重要**：本项目包含多个运行时数据文件，**不应将真实数据提交到 GitHub**。完整忽略规则见 `.gitignore`。

### 需要忽略的文件

以下文件已被 `.gitignore` 排除，或建议加入忽略：

- `functions/db/known_faces/*` — 人脸识别数据
- `functions/db/login_locks.json` — 登录锁定记录
- `functions/db/titles.json` — 身份验证题目与答案（**含学生真实姓名**，属于敏感信息）
- `functions/db/user_answers.json` — 用户答题记录
- `functions/db/bans.json` — 封禁记录
- `functions/db/ip_blacklist.json` — IP 黑名单
- `functions/db/rate_limits.json` — 速率限制记录（含 IP 与请求路径）
- `functions/config.py` — 可能包含数据库密码等配置

### 如果文件已被 Git 跟踪

`.gitignore` 只对**从未被跟踪**的文件生效。若上述文件曾经被提交过，需要先移出跟踪，再提交：

```bash
git rm --cached functions/db/titles.json
git rm --cached functions/db/user_answers.json
# 其他文件同理
git commit -m "停止跟踪敏感数据文件"
```

### 推荐做法

更安全的做法是**不在仓库中保留这些数据文件**，程序运行时自动创建空文件或从环境变量读取配置。如果确实需要在仓库中保留“空占位”，可使用 `git update-index --skip-worktree <文件>`，但需注意其对 `git pull` 的潜在影响。

## 问题反馈

如遇到问题或有改进建议，欢迎提交 Issue。

## License

MIT License © 2026 zfscjch