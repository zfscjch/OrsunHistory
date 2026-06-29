import ssl
from gevent import pywsgi
from orsun_server import app

# 证书文件路径
CERT_FILE = 'C:/HTML Projects/cjchcoderchat.site_other/cjchcoderchat.site_bundle.pem'
KEY_FILE = 'C:/HTML Projects/cjchcoderchat.site_other/cjchcoderchat.site.key'

# 创建 WSGIServer，直接传入SSL证书参数
server = pywsgi.WSGIServer(
    ('0.0.0.0', 3),
    app,
    keyfile=KEY_FILE,
    certfile=CERT_FILE,
    ssl_version=ssl.PROTOCOL_TLS_SERVER,
    ciphers='HIGH:!aNULL:!MD5'
)

print("Gevent WSGI server starting up on https://0.0.0.0:3 ...")

# 启动服务器，永久运行
server.serve_forever()
