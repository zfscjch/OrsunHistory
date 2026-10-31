#!/bin/bash
# OrsunHistory 自动化部署脚本
# 适用于 Ubuntu/Debian 系统，请使用 root 或 sudo 权限运行

set -e # 遇到错误立即退出

# ================= 配置区域 =================
PROJECT_NAME="OrsunHistory"
PROJECT_DIR="/var/www/orsunhistory"
GIT_REPO="https://github.com/zfscjch/OrsunHistory.git"
PYTHON_VERSION="python3"
VENV_DIR="$PROJECT_DIR/venv"
# MySQL 配置 (请提前在 MySQL 中创建好数据库和用户)
DB_NAME="orsunhistory_db"
DB_USER="orsun_user"
DB_PASSWORD="CHANGE_ME_TO_A_STRONG_PASSWORD"
# ===========================================

echo ">>> 1. 安装系统依赖 (Nginx, Python3, pip, venv, Git, MySQL客户端)"
apt update
apt install -y nginx python3 python3-pip python3-venv git mysql-client

echo ">>> 2. 克隆项目代码到 $PROJECT_DIR"
if [ -d "$PROJECT_DIR" ]; then
  echo "目录已存在，尝试更新代码..."
  cd "$PROJECT_DIR"
  git pull
else
  git clone "$GIT_REPO" "$PROJECT_DIR"
  cd "$PROJECT_DIR"
fi

echo ">>> 3. 创建并激活 Python 虚拟环境"
if [ ! -d "$VENV_DIR" ]; then
  $PYTHON_VERSION -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

echo ">>> 4. 安装 Python 依赖"
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
  pip install -r requirements.txt
else
  echo "警告: 未找到 requirements.txt，请手动检查项目依赖。"
  # 根据项目结构，Flask 核心依赖至少需要: pip install flask gunicorn
  pip install -r requirements.txt
fi

echo ">>> 5. 导入数据库结构"
# 假设 blog_db.sql 文件在项目根目录
if [ -f "blog_db.sql" ]; then
  echo "正在导入数据库结构到 $DB_NAME ..."
  # 此处需要你输入 MySQL root 密码或提前配置好 .my.cnf
  mysql -u root -p "$DB_NAME" < blog_db.sql
  echo "数据库导入完成。请确保数据库用户 '$DB_USER' 拥有对 '$DB_NAME' 的权限。"
else
  echo "警告: 未找到 blog_db.sql，请手动初始化数据库。"
fi

echo ">>> 6. 创建 Gunicorn 系统服务"
# 使用项目中的 run.py 作为入口，假设其中定义了 `app` 对象
cat > /etc/systemd/system/orsunhistory.service <<EOF
[Unit]
Description=Gunicorn instance for OrsunHistory
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$VENV_DIR/bin"
# 根据项目实际情况，可能需要设置环境变量，例如数据库连接信息
# Environment="DATABASE_URL=mysql://$DB_USER:$DB_PASSWORD@localhost/$DB_NAME"
ExecStart=$VENV_DIR/bin/gunicorn --workers 3 --bind unix:$PROJECT_DIR/orsunhistory.sock -m 007 run:app

[Install]
WantedBy=multi-user.target
EOF

echo ">>> 7. 配置 Nginx 反向代理"
cat > /etc/nginx/sites-available/orsunhistory <<EOF
server {
    listen 80;
    server_name your_domain.com; # 请替换为你的域名或公网 IP

    location / {
        include proxy_params;
        proxy_pass http://unix:$PROJECT_DIR/orsunhistory.sock;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade"; # 支持 WebSocket (项目使用了 Socket.IO)
        proxy_http_version 1.1;
    }

    location /static/ {
        alias $PROJECT_DIR/static/;
        expires 30d;
    }
}
EOF

# 启用 Nginx 站点配置
ln -sf /etc/nginx/sites-available/orsunhistory /etc/nginx/sites-enabled/
# 移除默认站点(可选)，避免冲突
rm -f /etc/nginx/sites-enabled/default

echo ">>> 8. 调整文件权限"
chown -R www-data:www-data "$PROJECT_DIR"
# 确保 Gunicorn 能创建 sock 文件
chmod 755 "$PROJECT_DIR"

echo ">>> 9. 启动服务并设置开机自启"
systemctl daemon-reload
systemctl start orsunhistory
systemctl enable orsunhistory
systemctl restart nginx

echo ">>> 10. 防火墙配置提醒"
echo "请确保已通过 'ufw' 或云控制台安全组放行 80 (HTTP) 和 443 (HTTPS) 端口。"
echo "如果是 ufw, 可执行: ufw allow 'Nginx Full'"

echo "=========================================="
echo "部署脚本执行完毕！"
echo "请检查以下事项："
echo "1. 确认 Nginx 配置中的 'server_name' 已替换为你的域名或 IP。"
echo "2. 确认 MySQL 数据库 '$DB_NAME' 已创建，且用户 '$DB_USER' 有权限访问。"
echo "3. 检查项目是否有其他环境变量或配置需要在 orsunhistory.service 中设置。"
echo "4. 访问 http://你的域名或IP 验证网站是否正常运行。"
echo "=========================================="