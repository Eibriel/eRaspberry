import os
import json

from flask import abort
from flask import request
from flask import jsonify
from flask import Blueprint
from flask import render_template

main = Blueprint('main', __name__)


@main.route('/message', methods=['POST'])
def message():
    print("MESSAGE")
    print(request)
    print(request.args)
    print(request.form)
    print(request.data)
    dataDict = request.form
    print(dataDict)
    data = {
        "message": dataDict["message"]
    }
    with open("status_keyboard.json", 'w', encoding='utf-8') as status_file:
        json.dump(data, status_file, sort_keys=True, indent=4, separators=(',', ': '))
    return jsonify({})


@main.route('/using_keyboard', methods=['GET'])
def using_keyboard():
    with open('using_keyboard', 'w') as f:
        f.write("using_keyboard")
    return jsonify({})


@main.route('/using_mic', methods=['GET'])
def using_mic():
    os.remove("using_keyboard")
    return jsonify({})


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
