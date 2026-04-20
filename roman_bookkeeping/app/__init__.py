from flask import Flask

from .auth import auth_bp
from .config import Config
from .db import init_app as init_db_app
from .views import main_bp
from .cli import init_app as init_cli_app


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(config_class)

    init_db_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    init_cli_app(app)

    return app
