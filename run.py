from gevent import pywsgi
from orsun_server import app  # 导入你的Flask应用

# 你的证书文件路径（从腾讯云下载的）
CERT_FILE = 'C:/HTML Projects/cjchcoderchat.site_other/cjchcoderchat.site_bundle.pem'
KEY_FILE = 'C:/HTML Projects/cjchcoderchat.site_other/cjchcoderchat.site.key'

# 创建 WSGIServer，直接传入SSL证书参数
server = pywsgi.WSGIServer(
    ('0.0.0.0', 3),  # 保持你用3端口（虽然不太常见，但尊重你的选择）
    app,
    keyfile=KEY_FILE,
    certfile=CERT_FILE
)

print("Gevent WSGI server starting up on https://0.0.0.0:3 ...")

# 启动服务器，永久运行
server.serve_forever()
