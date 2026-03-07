#!/bin/bash
# EC2 初回セットアップスクリプト（Amazon Linux 2）

set -e

sudo yum update -y
sudo yum install -y python3 python3-pip nginx git

cd /home/ec2-user
git clone <YOUR_REPO_URL> weekly-report
cd weekly-report

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# .env を設定してから実行
cp .env.example .env
# nano .env  # 実際の値を設定

export DJANGO_SETTINGS_MODULE=weekly_report.settings_production
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py init_data

# Gunicorn をsystemdに登録
sudo cp deploy/gunicorn.service /etc/systemd/system/
sudo systemctl enable gunicorn
sudo systemctl start gunicorn

# Nginx 設定
sudo cp deploy/nginx.conf /etc/nginx/conf.d/weekly-report.conf
sudo systemctl enable nginx
sudo systemctl restart nginx
