#!/bin/bash
set -o errexit

apt-get update
apt-get install -y libjpeg-dev zlib1g-dev

pip install --upgrade pip
pip install -r requirements.txt
python manage.py collectstatic --no-input