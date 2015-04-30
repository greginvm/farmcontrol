from flask import render_template, redirect, request, url_for, flash, session, current_app
from flask.ext.login import login_user, logout_user, login_required, current_user
from flask.ext.babel import gettext

from . import auth
from .forms import LoginForm
from ..models import User


@auth.before_app_request
def before_request():
    if current_user.is_authenticated():
        current_user.ping()


@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            session['charts_enabled'] = form.charts_enabled.data
            redirect_next = redirect(request.args.get('next') or url_for('dashboard.index'))
            response = current_app.make_response(redirect_next)
            response.set_cookie('charts_enabled', value='T' if form.charts_enabled.data else 'F')
            return response
        flash(gettext('Invalid username or password.'))
    return render_template('auth/login.html', form=form)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash(gettext('You have been logged out.'))
    return redirect(url_for('dashboard.index'))


