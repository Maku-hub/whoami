## Application Setup Guide

Hosting: VPS behind Cloudflare, port 20981  
OS: Alpine Linux

1. Install system dependencies:
    * `Python` 3.12+
    * `Nginx` 1.26.3+
    * `MariaDB`

2. Place files:
    * Copy the `nginx` directory to `/etc/nginx`
    * Copy the `html` directory to `/var/www/html`
    * Copy the `flashapp` file to `/etc/init.d/flaskapp`

3. Initialize the database (MariaDB):
```bash
mysql -u <USER_NAME> -p<USER_PASSWORD> -h <IP_ADDR> <DATABASE_NAME>

SHOW TABLES;

CREATE TABLE user_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_agent VARCHAR(255),
    app_name VARCHAR(255),
    platform VARCHAR(255),
    vendor VARCHAR(255),
    language VARCHAR(10),
    online BOOLEAN,
    cookies_enabled BOOLEAN,
    screen_width INT,
    screen_height INT,
    color_depth INT,
    pixel_depth INT,
    inner_width INT,
    inner_height INT,
    outer_width INT,
    outer_height INT,
    timezone_offset INT,
    `current_time` DATETIME,
    touch_support BOOLEAN,
    max_touch_points INT,
    device_memory FLOAT,
    public_ip VARCHAR(45),
    supplier VARCHAR(255),
    country VARCHAR(255),
    region VARCHAR(255),
    latitude DECIMAL(10, 6),
    longitude DECIMAL(10, 6),
    timezone VARCHAR(255),
    connection_type VARCHAR(50),
    downlink FLOAT,
    rtt INT,
    battery_level FLOAT,
    charging BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DESCRIBE user_data;
```

4. Configure Flask database connection. In `html/flask/app.py`, edit the `db_config` object with your credentials.

5. Set up and run Flask in a virtual environment
```bash
cd /var/www/html/flask
python -m venv web-venv
source web-venv/bin/activate
pip install flask flask-cors mysql-connector-python gunicorn
#gunicorn -w 4 -b 127.0.0.1:5000 app:app
deactivate
```    
Tip: Run Gunicorn in the directory containing app.py, otherwise Flask may not find module.

6. Update permissions and start flask application served by Gunicorn:
```bash
sudo chown -R nginx:nginx /var/log/flaskapp.log
sudo chown -R nginx:nginx /var/www/html/flask

sudo chmod +x /etc/init.d/flaskapp
sudo rc-update add flaskapp default

sudo rc-service flaskapp start
sudo rc-service flaskapp status
```

7. Add additional files:
    * Add `html/files/verification` (for https://moje.cert.pl/ verification)
    * Add CV file at `html/files/pub_CV_Mateusz_Maczewski.pdf` (or update `html/index.html` with your file name)

8. Restart `nginx`.
