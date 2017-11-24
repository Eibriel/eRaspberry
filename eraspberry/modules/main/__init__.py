import os
import json

from flask import abort
from flask import jsonify
from flask import Blueprint
from flask import render_template

main = Blueprint('main', __name__)


@main.route('/start', methods=['GET'])
def start():
    with open('lock', 'w') as f:
        f.write("lock")
    return render_template("start.html")


@main.route('/ui', methods=['GET'])
def ui():
    os.remove("lock")
    return render_template("main.html")


@main.route('/status', methods=['GET'])
def status():
    status_path = "status.json"
    if not os.path.exists(status_path):
        abort(500)
    else:
        with open(status_path, encoding='utf-8') as data_file:
            try:
                data = json.load(data_file)
            except:
                abort(500)
    return jsonify(data)
