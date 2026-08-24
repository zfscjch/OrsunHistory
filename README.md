# 翱三通史官网

## 【项目简介】

翱三通史官网是为记录奥山实验初级中学2023届3班初中生活而创立网站。网站储存和展示了本届的教师传记和学生传记。其中，教师传记储存在articles表中，学生传储存在students表中。网址：[https://www.cjchcoderchat.site:3/](https://www.cjchcoderchat.site:3/)。
此网站在`2026年中考前(2026年6月22日)`禁止教师访问。

## 【技术栈】
Python(Flask), HTML, JavaScript等。

## 【项目结构】
```text
OrsunHistory/
├── orsun_server.py             # flask应用，处理各种请求
├── init.sql                    # MySQL数据库结构
├── students.sql                # blog_db中储存学生文章的表结构
├── comments.sql                # blog_db中储存article对应评论的表结构
├── run.py                      # 生产环境运行
├── package.json
├── package-lock.json
├── templates/                  # flask渲染模版
│   ├── 503.html                # 处理状态码503
│   ├── admin.html              # 管理员主页
│   ├── article.html            # 文章阅读器
│   ├── author.html             # 作者查看可编辑文章的网页
│   ├── avoid_titles.html       # 与secret.js一起使用，验证用户身份
│   ├── chat.html               # 聊天模块
│   ├── edit.html               # 作者编辑文章的网页
│   ├── face.html               # 识别人脸
│   ├── forum_board.html        # 论坛各个板块
│   ├── forum_index.html        # 论坛首页
│   ├── forum_new.html          # 新建论坛
│   ├── forum_not_found.html    # 404论坛页
│   ├── forum_thread.html       # 论坛内容
│   ├── help.html               # 帮转文档
│   ├── index.html              # 首页
│   ├── introduce.html          # 简介
│   ├── issue.html              # 申报错误
│   ├── log.html                # 管理员日志
│   ├── login.html              # 登录
│   ├── login_outdated.html     # 怀旧版登录 
│   ├── maintenance.html        # 控制维护模式
│   ├── mobileChat.html         # 移动端聊天模块
│   ├── not_allow.html          # 非法用户重定向
│   ├── runtime_error.html      # 自定义错误
│   ├── share.html              # 分享
│   ├── show_issues.html        # 管理员管理网站错误 
│   ├── upload_img.html         # 上传人脸
│   ├── user.html               # 用户个性化设置
│   ├── userPolicy.html         # 用户隐私协议
│   └── version.html            # 版本文件
├── static/                     # 储存静态文件
│   ├── css/
│   │   ├── article.css         # article.html和share.html的css
│   │   ├── chat.css            # 适配chat.html的css
│   │   ├── common.css          # index.html,introduce.html和author.html的css
│   │   ├── face.css            # face.html和upload_img.html的css
│   │   └── verify.css          # login.html和avoid_titles.html的css
│   ├── js/
│   │   ├── checkAdmin.js       # 检查用户是否是管理员
│   │   ├── marked.umd.js       # markdown渲染文件
│   │   ├── messageChannel.js   # 各标签页通讯接口（暂未启用）
│   │   ├── secret.js           # 验证用户身份
│   │   └── socket.io.js        # WebSocket接口，用于使chat.html连接服务器
│   ├── doc/
│   └── pics/
├── functions/                  # 主要函数实现
│   ├── __init__.py             # 包文件
│   ├── admin.py                # 管理员模块
│   ├── admin_locker.py         # 管理员登录
│   ├── api.py                  # 管理所有POST请求方法的模块
│   ├── api_response.py         # 翱三通史标准Response
│   ├── config.py               # 项目配置
│   ├── error_handlers.py       # 处理用户提交的错误
│   ├── face_recognizer.py      # 原人脸识别后台
│   ├── face_recognizer_new.py  # 新人脸识别后台
│   ├── forum.py                # 论坛后端
│   ├── get_titles.py           # 与secret.js和avoid_titles.html一起使用，验证用户身份
│   ├── get_user.py             # 配合人脸识别获取用户
│   ├── log.py                  # 网站日志记录
│   ├── psg_mgr.py              # 管理MySQL中的文章
│   ├── psg_reviewer.py         # 文章审核
│   ├── user_mgr.py             # 管理用户登录
│   ├── db/                     # 数据储存
│   │   ├── known_faces/        # 储存人脸识别信息
│   │   ├── login_locks.json
│   │   ├── titles.json
│   │   └── user_answers.json
│   └── test/                   # 存储测试文件
└── README.md                   # 项目介绍
```
