#!/bin/bash
# Production-ready gunicorn configuration with multiple workers
# This fixes the page freezing issue during downloads

gunicorn --bind 0.0.0.0:5000 \
  --workers 2 \
  --threads 4 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  main:app
