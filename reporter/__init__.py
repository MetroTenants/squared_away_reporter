from flask import Flask
from .views import views
from .auth import auth, login_manager
from .database import db_session
import os


def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv('SECRET_KEY')
    app.register_blueprint(auth)
    app.register_blueprint(views)
    login_manager.init_app(app)
    return app


# Exposing so can be picked up by Zappa
app = create_app()


@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()


if __name__ == "__main__":
    import sys
    app = create_app()
    try:
        port = int(sys.argv[1])
    except (IndexError, ValueError):
        port = 5000
    app.run(debug=True, port=port)
