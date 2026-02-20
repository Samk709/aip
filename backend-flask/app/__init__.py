from flask import Flask
import time
from .config import Config
from .db.extensions import db
from .api.routes import api_bp
from .models import init_models


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)

    db.init_app(app)
    app.register_blueprint(api_bp)

    @app.route("/")
    def home():
        from flask import render_template
        return render_template("index.html", asset_version=int(time.time()))

    with app.app_context():
        init_models()
        db.create_all()

    return app
