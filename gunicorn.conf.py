# Gunicorn configuration file
# This fixes the page freezing issue during downloads

import multiprocessing

# Server socket
bind = "0.0.0.0:5000"

# Worker processes
workers = 2
worker_class = "gthread"
threads = 8
worker_connections = 1000
timeout = 120
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Development
reload = False
preload_app = False
