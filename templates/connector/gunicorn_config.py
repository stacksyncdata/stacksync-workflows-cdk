# Gunicorn settings used to serve the connector in production.
# https://docs.gunicorn.org/en/stable/settings.html
bind = "0.0.0.0:8080"
workers = 2
threads = 4
timeout = 360
