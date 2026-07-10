import os
import logging
from datetime import datetime

from werkzeug.middleware.proxy_fix import ProxyFix
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import mysql.connector
from mysql.connector import pooling

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Apply the ProxyFix middleware to help Flask know it's behind a reverse proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# Only the site itself needs to POST collected data cross-origin. Restrict CORS
# to the public origin instead of allowing every website to reach the API.
# Override with the ALLOWED_ORIGIN env var if the domain changes.
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "https://frog02-20981.wykr.es")
CORS(app, resources={r"/save-user-data/*": {"origins": ALLOWED_ORIGIN}})

# Database configuration is read from the environment so credentials are never
# committed to the repository. Falls back to placeholders for local reference.
db_config = {
    "host": os.environ.get("DB_HOST", "<IP_ADDR>"),
    "user": os.environ.get("DB_USER", "<USER_NAME>"),
    "password": os.environ.get("DB_PASSWORD", "<USER_PASSWORD>"),
    "database": os.environ.get("DB_NAME", "<DATABASE_NAME>"),
}

# A small connection pool avoids opening a fresh TCP/auth handshake to MariaDB
# on every single request. Built lazily so the app can still boot if the DB is
# temporarily unavailable at startup.
_pool = None


def get_connection():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="whoami_pool",
            pool_size=int(os.environ.get("DB_POOL_SIZE", "5")),
            **db_config,
        )
    return _pool.get_connection()


# Accepted formats for the client-supplied `current_time`. The browser sends
# `new Date().toLocaleString()`, whose format depends on the visitor's locale,
# so we try several rather than rejecting (and dropping) the whole record.
_DATE_FORMATS = (
    "%d.%m.%Y, %H:%M:%S",   # pl / de style
    "%m/%d/%Y, %I:%M:%S %p",  # en-US
    "%Y-%m-%d %H:%M:%S",
    "%d/%m/%Y, %H:%M:%S",
)


def parse_current_time(value):
    """Best-effort parse of the client clock. Returns None if unparseable so the
    row is still stored (with a NULL time) instead of being rejected."""
    if not value:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except (ValueError, TypeError):
            continue
    logger.warning("Unparseable current_time value: %r", value)
    return None


REQUIRED_FIELDS = [
    'user_agent', 'app_name', 'platform', 'vendor', 'language', 'online', 'cookies_enabled',
    'screen_width', 'screen_height', 'color_depth', 'pixel_depth', 'inner_width', 'inner_height',
    'outer_width', 'outer_height', 'timezone_offset', 'current_time', 'touch_support', 'max_touch_points',
    'device_memory', 'public_ip', 'supplier', 'country', 'region', 'latitude', 'longitude', 'timezone',
    'connection_type', 'downlink', 'rtt', 'battery_level', 'charging',
]


@app.route('/save-user-data/', methods=['POST'])
def save_data():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "No data received"}), 400

    for field in REQUIRED_FIELDS:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    # Do NOT log the payload itself – it contains visitor personal data.
    logger.info("Received user data from %s", request.remote_addr)

    current_time = parse_current_time(data.get('current_time'))

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()

        sql = """
        INSERT INTO user_data (
            `user_agent`, `app_name`, `platform`, `vendor`, `language`, `online`, `cookies_enabled`,
            `screen_width`, `screen_height`, `color_depth`, `pixel_depth`, `inner_width`, `inner_height`,
            `outer_width`, `outer_height`, `timezone_offset`, `current_time`, `touch_support`, `max_touch_points`,
            `device_memory`, `public_ip`, `supplier`, `country`, `region`, `latitude`, `longitude`, `timezone`,
            `connection_type`, `downlink`, `rtt`, `battery_level`, `charging`
        )
        VALUES (
            %(user_agent)s, %(app_name)s, %(platform)s, %(vendor)s, %(language)s, %(online)s, %(cookies_enabled)s,
            %(screen_width)s, %(screen_height)s, %(color_depth)s, %(pixel_depth)s, %(inner_width)s, %(inner_height)s,
            %(outer_width)s, %(outer_height)s, %(timezone_offset)s, %(current_time)s, %(touch_support)s,
            %(max_touch_points)s, %(device_memory)s, %(public_ip)s, %(supplier)s, %(country)s, %(region)s,
            %(latitude)s, %(longitude)s, %(timezone)s, %(connection_type)s, %(downlink)s, %(rtt)s, %(battery_level)s, %(charging)s
        )
        """
        cursor.execute(sql, {field: data.get(field) for field in REQUIRED_FIELDS} | {'current_time': current_time})

        connection.commit()
        return jsonify({"message": "Data saved successfully"}), 201

    except mysql.connector.Error as err:
        logger.error("Database error: %s", err)
        return jsonify({"error": "Database error occurred"}), 500

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@app.route('/stats/', methods=['GET'])
def stats():
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM user_data")
        rows = cursor.fetchall()
        return render_template('stats.html', rows=rows)

    except mysql.connector.Error as err:
        logger.error("[MySQL Error] %s", err)
        return "Database connection failed.", 500

    except Exception as e:
        logger.exception("[Unexpected Error] %s", e)
        return "An unexpected error occurred.", 500

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@app.route('/health', methods=['GET'])
def health():
    """Lightweight liveness/readiness probe for monitoring."""
    try:
        connection = get_connection()
        connection.ping(reconnect=True, attempts=1)
        connection.close()
        return jsonify({"status": "ok"}), 200
    except mysql.connector.Error:
        return jsonify({"status": "degraded", "db": "unavailable"}), 503


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
