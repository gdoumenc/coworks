import traceback
from dataclasses import dataclass

from flask import flash
from flask import redirect
from flask import session
from flask import url_for
from flask_login import UserMixin
from flask_login import login_user
from flask_login import logout_user
from flask_wtf import FlaskForm
from wtforms import PasswordField
from wtforms import StringField
from wtforms.validators import DataRequired
from wtforms.validators import Email

from coworks import Blueprint, request
from coworks import entry
from util import render_html_template


class LoginForm(FlaskForm):
    """ Form for the login connection.
    """
    email = StringField("Email (login)", default='', validators=[DataRequired(), Email()])
    password = PasswordField("Mot de passe", default='', validators=[DataRequired()])


@dataclass
class User(UserMixin):
    email: str = None

    # def is_authenticated(self):
    #     return self.email

    def get_id(self):
        return self.email


class AccountBlueprint(Blueprint):

    def __init__(self, login_manager):
        super().__init__(name="account")

        @login_manager.user_loader
        def load_user(user_id):
            user = session.get('user')
            return User(**user) if user else None

    @entry(no_auth=True)
    def get_login(self):
        """Get login form."""
        form = LoginForm()
        return render_html_template("account/login.j2", form=form)

    @entry(no_auth=True)
    def post_login(self, email=None, password=None, next_url=None, remember=False, **kwargs):
        """Sign in."""
        try:
            form = LoginForm()
            print(f"Submitted {form.is_submitted()}")
            print(f"Form {request.form}")
            print(f"Validate {form.validate()}")
            if not form.validate_on_submit():
                print(form.errors)
                flash('Connexion refusée.', 'error')
                return render_html_template('account/login.j2', form=form)

            try:
                user = User(email)
                login_user(user, remember=remember)
                session['user'] = user

                flash('Logged in successfully.')
                return redirect(url_for('get'))
            except (Exception,) as e:
                flash(e, 'error')
        except (Exception,) as exc_obj:
            tb_str = ''.join(traceback.format_exception(None, exc_obj, exc_obj.__traceback__))
            print(tb_str)

    @entry(no_auth=True)
    def get_logout(self):
        logout_user()
        return redirect(url_for('get'))
