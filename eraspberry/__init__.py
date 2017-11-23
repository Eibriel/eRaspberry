from flask import Flask

app = Flask(__name__)

# DO NOT MOVE!
from eraspberry.modules.main import main

app.register_blueprint(main)
