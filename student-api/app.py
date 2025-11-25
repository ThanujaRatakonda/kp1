from flask import Flask, jsonify
import os
import sys
app = Flask(__name__)
@app.route("/students")
def get_students():
    return jsonify([
        {"id": 1, "name": "Thanuja"},
        {"id": 2, "name": "Teja"},
        {"id": 3, "name": "Ravi"},
        {"id": 4, "name": "Bob"},
    ])
@app.route("/")
def home():
    return "Student API Working!"
@app.route("/error")
def crash():
    os._exit(1)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
