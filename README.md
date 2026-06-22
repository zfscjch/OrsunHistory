# 翱三通史官网

## 【项目简介】

翱三通史官网是为记录奥山实验初级中学2023届3班初中生活而创立网站。网站储存和展示了本届的教师传记和学生传记。其中，教师传记储存在articles表中，学生传储存在students表中。网址：[https://www.cjchcoderchat.site:3/](https://www.cjchcoderchat.site:3/)。
此网站在`2026年中考`前禁止教师访问。

## 【项目结构】
```text
OrsunHistory/
├── orsun_server.py           # flask应用，处理各种请求
├── init.sql                  # MySQL数据库结构
├── students.sql              # blog_db中储存学生文章的表结构
├── comments.sql              # blog_db中储存article对应评论的表结构
├── user.backup.sql           # 用户数据备份
├── run.py                    # 生产环境运行
├── package.json
├── package-lock.json
├── start.bat                 # 开发环境运行
├── start_run.bat             # 生产环境运行
├── templates/                # flask渲染模版
│   ├── 503.html              # 处理状态码503
│   ├── author.html           # 作者查看可编辑文章的网页
│   ├── avoid_titles.html     # 与secret20260524.js一起使用，验证用户身份
│   ├── edit.html             # 作者编辑文章的网页
│   ├── index.html            # 首页
│   ├── introduce.html        # 简介
│   ├── login.html            # 登录
│   ├── maintenance.html      # 控制维护模式
│   ├── not_allow.html        # 非法用户重定向
│   ├── psg.html              # article表文章阅读器
│   └── students.html         # students表文章阅读器
├── static/                   # 储存静态文件
│   ├── js/
│   │   └── secret20260622.js # 验证用户身份
│   └── pics/
├── functions/                # 主要函数实现
│   ├── __init__.py           # 包文件
│   ├── admin_locker.py       # 管理员登录
│   ├── alert.py              # 向用户提示警告信息
│   ├── config.py             # 项目配置
│   ├── get_titles.py         # 与secret20260524.js和avoid_titles.html一起使用，验证用户身份
│   ├── psg_mgr.py            # 管理MySQL中的文章
│   ├── user_mgr.py           # 管理用户登录
│   ├── test(x).py            # 测试文件
│   ├── db/                   # 数据储存
│   │   ├── alerts.json
│   │   ├── login_locks.json
│   │   ├── titles.json
│   │   └── user_answers.json
│   └── test/                 # 存储测试文件
└── README.md                 # 项目介绍
```
