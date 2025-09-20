# webapp.py
from flask import Flask, request, jsonify, render_template
from executor import CommandExecutor
import os

app = Flask(__name__)
executor = CommandExecutor()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/exec", methods=["POST"])
def api_exec():
    data = request.get_json() or {}
    cmd = data.get("cmd", "")
    cwd = data.get("cwd", os.getcwd())
    out, err, new_cwd, code = executor.run(cmd, cwd)
    # If new_cwd is None (e.g., cpu/mem/ps), keep provided cwd
    if new_cwd is None:
        new_cwd = cwd
    return jsonify({
        "stdout": out,
        "stderr": err,
        "cwd": new_cwd,
        "code": code
    })

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)