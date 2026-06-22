#!/bin/bash
set -o errexit

apt-get update
apt-get install -y tesseract-ocr libtesseract-dev

pip install --upgrade pip
pip install -r requirements.txt
python manage.py collectstatic --no-input