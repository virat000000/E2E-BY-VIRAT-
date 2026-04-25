# gunicorn_config.py
bind = "0.0.0.0:%s" % os.environ.get("PORT", 8000)
workers = 4  # Multiple threads chalane ke liye
timeout = 30
accesslog = "-"
errorlog = "-"
capture_output = True
enable_stdio_inheritance = True
