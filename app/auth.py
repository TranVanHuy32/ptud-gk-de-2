import functools
import secrets
import os

from flask import (Blueprint, flash, g, redirect, render_template, request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from app.db import get_db

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'

        if error is None:
            try:
                # Tạo avatar mới cho user
                avatar_url = f"https://avatar-placeholder.iran.liara.run/public/{username}"
                db.execute(
                    "INSERT INTO user (username, password, avatar) VALUES (?, ?, ?)",
                    (username, generate_password_hash(password), avatar_url),
                )
                db.commit()
            except db.IntegrityError:
                error = f"User {username} is already registered."
            else:
                return redirect(url_for("auth.login"))

        flash(error)

    return render_template('auth/register.html')

@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None
        user = db.execute('SELECT * FROM user WHERE username = ?', (username,)).fetchone()

        if user is None:
            error = 'Incorrect username.'
        elif user and not check_password_hash(user['password'], password):
            error = 'Incorrect password.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('index'))

        flash(error)

    return render_template('auth/login.html')

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        user = get_db().execute(
            'SELECT * FROM user WHERE id = ?', (user_id,)
        ).fetchone()

        if user:
            user_dict = dict(user)
            is_blocked = user_dict.get('is_blocked')
            if is_blocked is not None and bool(is_blocked):
                g.user = None
                session.clear()
                flash('Tài khoản đã bị khóa. Mời đăng nhập lại.')
                return redirect(url_for('auth.login'))
            else:
                # Kiểm tra và thêm avatar nếu chưa có
                if 'avatar' not in user_dict or user_dict['avatar'] is None:
                    from .user import generate_avatar_url
                    avatar_url = generate_avatar_url(user_dict['username'])
                    db = get_db()
                    db.execute(
                        'UPDATE user SET avatar = ? WHERE id = ?',
                        (avatar_url, user_dict['id'])
                    )
                    db.commit()
                    user_dict['avatar'] = avatar_url
                g.user = user_dict
        else:
            g.user = None
        
@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@bp.route('/create_admin', methods=('GET', 'POST'))
def create_admin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        error = None

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'

        if error is None:
            try:
                db.execute(
                    "INSERT INTO user (username, password, role) VALUES (?, ?, ?)",
                    (username, generate_password_hash(password), 'admin'),  # Gán vai trò admin
                )
                db.commit()
            except db.IntegrityError:
                error = f"User {username} is already registered."
            else:
                return redirect(url_for("index"))  # Chuyển hướng đến trang blog

        flash(error)

    return render_template('auth/create_admin.html')  # Tạo template create_admin.html

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view

@bp.route('/admin/users', methods=('GET',))
@login_required
def admin_users():
    if g.user['role'] != 'admin':
        abort(403)  # Chỉ admin mới có quyền truy cập

    db = get_db()
    users = db.execute('SELECT id, username, role FROM user').fetchall()

    return render_template('admin/users.html', users=users)