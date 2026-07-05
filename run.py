import ssl
from gevent import pywsgi
from orsun_server import app

# 证书文件路径
CERT_FILE = 'C:/HTML Projects/cjchcoderchat.site_other/cjchcoderchat.site_bundle.pem'
KEY_FILE = 'C:/HTML Projects/cjchcoderchat.site_other/cjchcoderchat.site.key'


def create_ssl_context():
    """创建优化的 SSL 上下文"""
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)

    # 加载证书
    context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)

    # 协议设置
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_3

    # 禁用不安全的选项
    context.options |= ssl.OP_NO_SSLv2
    context.options |= ssl.OP_NO_SSLv3
    context.options |= ssl.OP_NO_TLSv1
    context.options |= ssl.OP_NO_TLSv1_1

    # 启用现代加密套件（广泛兼容）
    context.set_ciphers('ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384')

    # 可选：增加安全级别（某些旧客户端可能不兼容）
    # context.set_ciphers('DEFAULT@SECLEVEL=2')

    return context


# 创建 WSGIServer，直接传入SSL证书参数
ssl_context = create_ssl_context()
server = pywsgi.WSGIServer(
    ('0.0.0.0', 3), app,
    ssl_context=ssl_context
)

print("Gevent WSGI server starting up on https://0.0.0.0:3 ...")

# 启动服务器，永久运行
server.serve_forever()
