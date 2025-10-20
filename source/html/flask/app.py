from werkzeug.middleware.proxy_fix import ProxyFix
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import mysql.connector
from datetime import datetime

app = Flask(__name__)

# Apply the ProxyFix middleware to help Flask know it's behind a reverse proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

CORS(app)

# MySQL Database configuration
db_config = {
    'host': '<IP_ADDR>',
    'user': '<USER_NAME>',
    'password': '<USER_PASSWORD>',
    'database': '<DATABASE_NAME>'
}

@app.route('/save-user-data/', methods=['POST'])
def save_data():

    data = request.json

    if not data:
        return jsonify({"error": "No data received"}), 400

    # Log received data for debugging
    print("Received data:", data)

    # Required fields check
    required_fields = ['user_agent', 'app_name', 'platform', 'vendor', 'language', 'online', 'cookies_enabled',
                       'screen_width', 'screen_height', 'color_depth', 'pixel_depth', 'inner_width', 'inner_height',
                       'outer_width', 'outer_height', 'timezone_offset', 'current_time', 'touch_support', 'max_touch_points',
                       'device_memory', 'public_ip', 'supplier', 'country', 'region', 'latitude', 'longitude', 'timezone',
                       'connection_type', 'downlink', 'rtt', 'battery_level', 'charging']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    try:
        # Parse the date correctly
        current_time = datetime.strptime(data.get('current_time'), '%d.%m.%Y, %H:%M:%S')
    except ValueError:
        return jsonify({"error": "Invalid date format, expected: dd.mm.yyyy, hh:mm:ss"}), 400

    try:
        # Connect to the database
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Prepare the SQL statement
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
        # Execute the query
        cursor.execute(sql, {
            'user_agent': data.get('user_agent'),
            'app_name': data.get('app_name'),
            'platform': data.get('platform'),
            'vendor': data.get('vendor'),
            'language': data.get('language'),
            'online': data.get('online'),
            'cookies_enabled': data.get('cookies_enabled'),
            'screen_width': data.get('screen_width'),
            'screen_height': data.get('screen_height'),
            'color_depth': data.get('color_depth'),
            'pixel_depth': data.get('pixel_depth'),
            'inner_width': data.get('inner_width'),
            'inner_height': data.get('inner_height'),
            'outer_width': data.get('outer_width'),
            'outer_height': data.get('outer_height'),
            'timezone_offset': data.get('timezone_offset'),
            'current_time': current_time,
            'touch_support': data.get('touch_support'),
            'max_touch_points': data.get('max_touch_points'),
            'device_memory': data.get('device_memory'),
            'public_ip': data.get('public_ip'),
            'supplier': data.get('supplier'),
            'country': data.get('country'),
            'region': data.get('region'),
            'latitude': data.get('latitude'),
            'longitude': data.get('longitude'),
            'timezone': data.get('timezone'),
            'connection_type': data.get('connection_type'),
            'downlink': data.get('downlink'),
            'rtt': data.get('rtt'),
            'battery_level': data.get('battery_level'),
            'charging': data.get('charging')
        })

        # Commit changes
        connection.commit()

        return jsonify({"message": "Data saved successfully"}), 201

    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return jsonify({"error": "Database error occurred"}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

@app.route('/stats/', methods=['GET'])
def stats():
    try:
        # Connect to the database
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)

        # Query to fetch data from the database
        cursor.execute("SELECT * FROM user_data")
        rows = cursor.fetchall()

        # Pass data to the template
        return render_template('stats.html', rows=rows)

    except mysql.connector.Error as err:
        print(f"[MySQL Error] {err}")
        return "Database connection failed.", 500

    except Exception as e:
        print(f"[Unexpected Error] {e}")
        return "An unexpected error occurred.", 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
