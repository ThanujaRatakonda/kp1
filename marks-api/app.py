
from flask import Flask, jsonify
import os
app = Flask(__name__)

@app.route("/marks")
def get_marks():
    return jsonify([
        {"student_id": 1, "marks": 48},
        {"student_id": 2, "marks": 81},
        {"student_id": 3, "marks": 35},
        {"student_id": 5, "marks": 67},
    ])

@app.route("/")
def home():
    return "Marks API Working!"
@app.route("/error")
def crash():
    os._exit(1)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4000)
