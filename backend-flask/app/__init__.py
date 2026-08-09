from flask import Flask
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
        return render_template("landing.html")

    @app.route("/dashboard")
    def dashboard():
        from flask import render_template
        return render_template("dashboard.html")

    @app.route("/chat")
    def chat_page():
        from flask import render_template
        return render_template("chat.html")

    @app.route("/admin")
    def admin_page():
        from flask import render_template
        return render_template("admin.html")

    @app.route("/about")
    def about():
        from flask import render_template
        return render_template("about.html")

    @app.route("/features")
    def features():
        from flask import render_template
        return render_template("features.html")

    @app.route("/research")
    def research():
        from flask import render_template
        return render_template("research.html")

    @app.route("/analytics")
    def analytics():
        from flask import render_template
        return render_template("analytics.html")

    @app.route("/privacy")
    def privacy():
        from flask import render_template
        return render_template("privacy.html")

    with app.app_context():
        init_models()
        db.create_all()

    return app
