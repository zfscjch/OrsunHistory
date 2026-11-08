from gevent import pywsgi
from orsun_server import app
from functions import Config

app.config['SESSION_COOKIE_SECURE'] = True

server = pywsgi.WSGIServer(
    ('0.0.0.0', 3),
    app,
    keyfile=Config.KEY_FILE,
    certfile=Config.CERT_FILE
)

print("Gevent WSGI server starting up on https://0.0.0.0:3 ...")
server.serve_forever()
