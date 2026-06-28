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
├── run.py                    # 生产环境运行
├── package.json
├── package-lock.json
├── templates/                # flask渲染模版
│   ├── 503.html              # 处理状态码503
│   ├── article.html          # 文章阅读器
│   ├── author.html           # 作者查看可编辑文章的网页
│   ├── avoid_titles.html     # 与secret20260524.js一起使用，验证用户身份
│   ├── edit.html             # 作者编辑文章的网页
│   ├── face.html             # 识别人脸
│   ├── index.html            # 首页
│   ├── introduce.html        # 简介
│   ├── log.html              # 管理员日志
│   ├── login.html            # 登录
│   ├── maintenance.html      # 控制维护模式
│   ├── not_allow.html        # 非法用户重定向
│   ├── runtime_error.html    # 自定义错误
│   ├── upload_img.html       # 上传人脸
│   ├── user.html             # 用户个性化设置
│   └── userPolicy.html       # 用户隐私协议
├── static/                   # 储存静态文件
│   ├── js/
│   │   ├── checkAdmin.js     # 检查用户是否是管理员
│   │   └── secret20260628.js # 验证用户身份
│   └── pics/
├── functions/                # 主要函数实现
│   ├── __init__.py           # 包文件
│   ├── admin_locker.py       # 管理员登录
│   ├── api_response.py       # 翱三通史标准web response
│   ├── config.py             # 项目配置
│   ├── error_handlers.py     # 处理用户提交的错误
│   ├── face_recognizer.py    # 人脸识别后台
│   ├── get_titles.py         # 与secret20260524.js和avoid_titles.html一起使用，验证用户身份
│   ├── get_user.py           # 配合人脸识别获取用户
│   ├── log.py                # 网站日志
│   ├── psg_mgr.py            # 管理MySQL中的文章
│   ├── psg_reviewer.py       # 文章审核
│   ├── user_mgr.py           # 管理用户登录
│   ├── db/                   # 数据储存
│   │   ├── known_faces/      # 储存人脸识别信息
│   │   ├── login_locks.json
│   │   ├── titles.json
│   │   └── user_answers.json
│   └── test/                 # 存储测试文件
└── README.md                 # 项目介绍
```
