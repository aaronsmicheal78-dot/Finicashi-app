import os

worker_class = "gevent"
workers = 4
threads = 2
worker_connections = 1000
timeout = 120
bind = "0.0.0.0:{}".format(os.getenv("PORT", "10000"))

loglevel = "info"
accesslog = "-"
errorlog = "-"
