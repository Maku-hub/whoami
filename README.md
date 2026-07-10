# whoami

Personal landing page with a lightweight visitor-analytics backend.

The site serves a single animated landing page (`html/index.html`) and, on load,
collects technical information about the visitor's browser, device, network and
approximate geolocation. The data is sent to a small Flask API, stored in MariaDB
and can be browsed on an authenticated `/stats/` page.

**Live:**  <https://maku-hub.github.io/whoami> (<https://frog02-20981.wykr.es>)

## Tech stack

- **Frontend:** static HTML/CSS/JS, [particles.js](https://vincentgarreau.com/particles.js/) (self-hosted)
- **Backend:** Python 3.12+, Flask + Gunicorn
- **Database:** MariaDB / MySQL
- **Web server / reverse proxy:** Nginx (Alpine, OpenRC service)

## Repository layout

```text
.
├── index.html            # GitHub Pages redirect to the live site
├── flaskapp              # OpenRC init script (-> /etc/init.d/flaskapp)
├── nginx/                # Nginx config (-> /etc/nginx)
│   ├── nginx.conf
│   ├── security.conf     # security headers + CSP
│   ├── mime.types
│   └── http.d/default.conf
└── html/                 # Web root (-> /var/www/html)
    ├── index.html        # landing page
    ├── robots.txt
    ├── css/ · icons/ · scripts/ · errors/
    ├── files/            # served static files (CV, verification token — git-ignored)
    └── flask/            # data-collection API
        ├── app.py
        ├── requirements.txt
        └── templates/stats.html
```

## Setup guide

Hosting: VPS behind Cloudflare, port 20981 · OS: Alpine Linux

### 1. Install system dependencies

- `Python` 3.12+
- `Nginx` 1.26.3+
- `MariaDB`

### 2. Place files

When redeploying over a live server, back up first (used by the rollback below):

```bash
cp -a /etc/nginx       /etc/nginx.bak.$(date +%F)
cp -a /var/www/html    /var/www/html.bak.$(date +%F)
```

Then copy the files:

- Copy the `nginx` directory to `/etc/nginx`
- Copy the `html` directory to `/var/www/html`
- Copy the `flaskapp` file to `/etc/init.d/flaskapp`

Use plain `cp -r` (not `rsync --delete`) so server-only files under
`/var/www/html/files/` (CV, verification token) are not removed.

### 3. Initialize the database (MariaDB)

```sql
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_public_ip (public_ip),
    INDEX idx_created_at (created_at)
);
```

#### Resetting the database

To wipe all collected data and recreate the table from scratch (⚠️ destructive —
back up first), drop and re-run the `CREATE TABLE` above:

```bash
# 1. Back up existing data
mysqldump -u <USER_NAME> -p<USER_PASSWORD> -h <IP_ADDR> <DATABASE_NAME> > user_data.backup.sql

# 2. Drop the table, then paste the CREATE TABLE statement again
mysql -u <USER_NAME> -p<USER_PASSWORD> -h <IP_ADDR> <DATABASE_NAME> -e "DROP TABLE IF EXISTS user_data;"
```

To only clear rows while keeping the table definition, use
`TRUNCATE TABLE user_data;` instead (this also resets `AUTO_INCREMENT`).

> Passwords passed on the command line land in shell history and `ps`; clear with
> `history -c` if that matters on your host.

### 4. Configure the database connection

Credentials are read from environment variables (no secrets in the repo). Set them
for the service, e.g. in `/etc/conf.d/flaskapp` (OpenRC sources this automatically):

```bash
export DB_HOST=<IP_ADDR>
export DB_USER=<USER_NAME>
export DB_PASSWORD=<USER_PASSWORD>
export DB_NAME=<DATABASE_NAME>
# optional:
# export DB_POOL_SIZE=5
# export ALLOWED_ORIGIN=https://frog02-20981.wykr.es
```

If a variable is missing the app falls back to a `<PLACEHOLDER>`, so DB calls fail
until real values are provided.

### 5. Set up the Python virtual environment

```bash
cd /var/www/html/flask
python -m venv web-venv
source web-venv/bin/activate
pip install -r requirements.txt
deactivate
```

Tip: run Gunicorn from the directory containing `app.py`, otherwise Flask may not
find the module.

### 6. Set permissions and start the service

The Nginx worker runs as user `nginx` and must be able to read the whole web root,
otherwise the site returns **403 Forbidden**:

```bash
# Web root readable by nginx
sudo chown -R nginx:nginx /var/www/html
sudo find /var/www/html -type d -exec chmod 755 {} \;
sudo find /var/www/html -type f -exec chmod 644 {} \;

sudo chown nginx:nginx /var/log/flaskapp.log

# OpenRC service (the init script must have LF line endings — see Troubleshooting)
sudo chmod +x /etc/init.d/flaskapp
sudo rc-update add flaskapp default

sudo rc-service flaskapp start
sudo rc-service flaskapp status
```

### 7. Add deployment-specific files

These are intentionally git-ignored — add them on the server:

- `/var/www/html/files/verification` — for [moje.cert.pl](https://moje.cert.pl/) verification
- `/var/www/html/files/pub_CV_Mateusz_Maczewski.pdf` — CV (or update `html/index.html` with your filename)

### 8. Protect the `/stats/` page

The `/stats/` page exposes collected visitor data, so it is behind HTTP Basic Auth:

```bash
sudo apk add apache2-utils          # provides htpasswd
sudo htpasswd -c /etc/nginx/.htpasswd <username>   # prompts for a password

# The nginx worker must be able to read the file AND traverse /etc/nginx,
# otherwise /stats/ returns 500 after login:
sudo chmod 755 /etc/nginx
sudo chown root:root /etc/nginx/.htpasswd
sudo chmod 644 /etc/nginx/.htpasswd
```

`<username>` is a login you choose; `htpasswd` then asks for the password. Use `-c`
only the first time (it recreates the file); omit it to add more users. Avoid weak
credentials — this page exposes visitor data.

### 9. Restart Nginx

```bash
sudo nginx -t && sudo rc-service nginx reload
```

### 10. Verify the deployment

```bash
# API is up and can reach the database:
curl -s http://127.0.0.1:5000/health            # -> {"status":"ok"}

# /stats/ requires authentication:
curl -sI https://frog02-20981.wykr.es/stats/    # -> 401 without credentials

# Landing page is served:
curl -sI https://frog02-20981.wykr.es/          # -> 200
```

In the browser also check:

- The landing page loads fully (particles, icons, fonts) with **no CSP errors** in
  the dev console (F12) — particles.js is self-hosted, so it should be clean.
- `/stats/` prompts for the Basic Auth login and shows data after signing in.
- Open the site in a private window, then confirm a **new row** appears in `/stats/`
  (i.e. saving to the database works).
- `tail /var/log/flaskapp.log` shows no database/import errors.

The API also exposes `GET /health` for ongoing liveness/readiness monitoring
(returns `{"status": "ok"}` when the database is reachable).

## Rollback

If something breaks, restore the backups taken before deployment:

```bash
sudo rc-service flaskapp stop
rm -rf /etc/nginx     && mv /etc/nginx.bak.<date>     /etc/nginx
rm -rf /var/www/html  && mv /var/www/html.bak.<date>  /var/www/html
sudo nginx -t && sudo rc-service nginx reload
sudo rc-service flaskapp start
```
