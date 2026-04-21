import time
import json
import requests
from flask import Flask, render_template, Response, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ThingSpeak channel details
THINGSPEAK_CHANNEL_ID = 3344343
THINGSPEAK_READ_API_KEY = "QLAFPI5MBZULYRTP"   # your read key (if channel is private)
# If channel is public, you can omit the API key.

# Global variable to hold latest patient data
latest_data = {
    "id": "IVMonitor01",
    "name": "John Doe",
    "bed": "Bed 12A",
    "ward": "ICU",
    "flowRate": 0,
    "dropCount": 0,
    "remainingFluid": 500,
    "mode": "AUTO",
    "targetFlowRate": 100,
    "servoAngle": 90,
    "status": "normal"
}

def fetch_from_thingspeak():
    """Fetch the latest field values from ThingSpeak."""
    url = f"https://api.thingspeak.com/channels/{THINGSPEAK_CHANNEL_ID}/feeds/last.json"
    if THINGSPEAK_READ_API_KEY:
        url += f"?api_key={THINGSPEAK_READ_API_KEY}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            flow = float(data.get('field1', 0))
            drops = int(float(data.get('field2', 0)))
            remaining = float(data.get('field3', 500))
            return flow, drops, remaining
    except Exception as e:
        print(f"ThingSpeak error: {e}")
    # Fallback to mock data if ThingSpeak fails
    import random
    flow = random.uniform(80, 120)
    drops = int(flow / 60 * 20)
    remaining = max(0, 500 - random.uniform(0, 2))
    return flow, drops, remaining

def update_patient_data():
    """Update the global latest_data dictionary from ThingSpeak."""
    global latest_data
    flow, drops, remaining = fetch_from_thingspeak()
    latest_data["flowRate"] = round(flow, 1)
    latest_data["dropCount"] = drops
    latest_data["remainingFluid"] = round(remaining, 0)

    # Determine status based on remaining fluid
    if remaining < 50:
        latest_data["status"] = "critical"
    elif remaining < 150:
        latest_data["status"] = "warning"
    else:
        latest_data["status"] = "normal"

    # Mode and target are stored in the frontend / local settings,
    # but you could also read them from ThingSpeak fields 4-6 if you send them.
    # Here we keep them as they were.

# SSE stream: sends new data to all connected clients every 2 seconds
@app.route('/stream')
def stream():
    def event_stream():
        while True:
            update_patient_data()
            yield f"data: {json.dumps(latest_data)}\n\n"
            time.sleep(2)
    return Response(event_stream(), mimetype="text/event-stream")

# Routes for pages
@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/patient/<patient_id>')
def patient_detail(patient_id):
    # For now we only have one patient; you can expand to multiple
    return render_template('patient_detail.html', patient_id=patient_id)

@app.route('/alerts')
def alerts():
    return render_template('alerts.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

# API endpoint to receive control commands from the frontend
@app.route('/control', methods=['POST'])
def control():
    data = request.json
    command = data.get('command')
    value = data.get('value')
    print(f"Control command received: {command} = {value}")
    # Here you would send the command to your ESP8266/Arduino
    # e.g., via serial, MQTT, or HTTP to Blynk's API.
    # For now, we just log and return success.
    return jsonify({"status": "ok", "command": command, "value": value})

if __name__ == '__main__':
    # Start background thread to pre-fetch data? Not needed because SSE does it.
    print("🚀 Starting Flask Server...")
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)