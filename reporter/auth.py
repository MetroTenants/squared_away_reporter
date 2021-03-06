from functools import wraps

from flask import Blueprint
from flask import current_app as app  # noqa
from flask import redirect, render_template, request, url_for
from flask_login import LoginManager, current_user, login_user, logout_user
from flask_wtf import Form
from sqlalchemy import func
from wtforms import PasswordField, TextField
from wtforms.validators import DataRequired

from .database import db_session
from .models import User

auth = Blueprint("auth", __name__)

login_manager = LoginManager()


class LoginForm(Form):
    email = TextField("email", validators=[DataRequired()])
    password = PasswordField("password", validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)
        self.user = None

    def validate(self):
        rv = Form.validate(self)
        if not rv:
            return False

        user = (
            db_session.query(User)
            .filter(
                func.lower(User.email) == func.lower(self.email.data),
                User.role.in_(["admin", "callcenter"]),
            )
            .first()
        )
        if user is None:
            self.email.errors.append("Email address is not registered")
            return False

        if not user.check_password(user.email, self.password.data):
            self.password.errors.append("Password is not valid")
            return False

        self.user = user
        return True


@login_manager.user_loader
def load_user(userid):
    return db_session.query(User).get(userid)


@login_manager.unauthorized_handler
def handle_needs_login():
    return redirect(url_for("auth.login", next=request.path))


@auth.route("/login/", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = form.user
        login_user(user)
        redirect_next = url_for("views.index")
        if request.args.get("next"):
            redirect_next = request.args.get("next")
        return redirect(redirect_next)
    email = form.email.data
    return render_template("login.html", form=form, email=email)


@auth.route("/logout/")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


def admin_required(f):
    """Restrict view to users with 'admin' role"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user is None or current_user.role != "admin":
            return redirect(url_for("auth.login", next=request.url))
        return f(*args, **kwargs)

    return decorated_function
