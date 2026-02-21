from flask import Flask
import time
from pathlib import Path
from .config import Config
from .db.extensions import db
from .api.routes import api_bp
from .models import init_models


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
    app.config["INSTANCE_LABEL"] = f"{Path.cwd().name}:{app.config['BUILD_MARKER']}"

    db.init_app(app)
    app.register_blueprint(api_bp)

    @app.after_request
    def add_no_cache_headers(response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    @app.route("/")
    def home():
        from flask import render_template
        return render_template(
            "index.html",
            asset_version=int(time.time()),
            instance_label=app.config["INSTANCE_LABEL"],
            build_marker=app.config["BUILD_MARKER"],
        )

    with app.app_context():
        init_models()
        db.create_all()

    return app
