from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)

API_TOKEN = "ObiSOARBlocker2026!"

@app.route("/block", methods=["POST"])
def block_ip():
    token = request.headers.get("X-API-Key")
    if token != API_TOKEN:
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    ip = data.get("ip")

    if not ip:
        return jsonify({"error": "missing ip"}), 400

    result = subprocess.run(
        ["sudo", "/usr/local/bin/block_ip.sh", ip],
        capture_output=True,
        text=True
    )

    return jsonify({
        "ip": ip,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr
    }), 200 if result.returncode == 0 else 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)