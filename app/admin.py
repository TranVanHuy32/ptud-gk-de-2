import logging
import secrets
import random
import string
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash, g, abort, session
from werkzeug.security import generate_password_hash

from app.auth import login_required
from app.db import get_db

bp = Blueprint('admin', __name__, url_prefix='/admin')

def get_user_by_id(id):
    db = get_db()
    user = db.execute('SELECT * FROM user WHERE id = ?', (id,)).fetchone()
    if user:
        user = dict(user)
        user['is_blocked'] = bool(user['is_blocked'])
    return user

@bp.route('/users')
@login_required
def users():
    if g.user['role'] != 'admin':
        return redirect(url_for('index'))

    db = get_db()
    users = db.execute('SELECT * FROM user').fetchall()
    return render_template('admin/users.html', users=users)

@bp.route('/users/create', methods=('GET', 'POST'))
@login_required
def create_user():
    if g.user['role'] != 'admin':
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

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
                    (username, generate_password_hash(password), role),
                )
                db.commit()
            except db.IntegrityError:
                error = f"User {username} is already registered."
            else:
                return redirect(url_for("admin.users"))

        flash(error)

    return render_template('admin/create_user.html')

@bp.route('/users/<int:id>/block', methods=['POST'])
@login_required
def block_user(id):
    if g.user['role'] != 'admin':
        return redirect(url_for('index'))

    user = get_user_by_id(id)
    if not user:
        abort(404)

    if user and user['id'] == session.get('user_id'):
        session.clear()
        

    db = get_db()
    db.execute('UPDATE user SET is_blocked = 1 WHERE id = ?', (id,))
    db.commit()

    return redirect(url_for('admin.users'))

@bp.route('/users/<int:id>/unblock', methods=['POST'])
@login_required
def unblock_user(id):
    if g.user['role'] != 'admin':
        return redirect(url_for('index'))

    user = get_user_by_id(id)
    if not user:
        abort(404)

    db = get_db()
    db.execute('UPDATE user SET is_blocked = 0 WHERE id = ?', (id,))
    db.commit()

    return redirect(url_for('admin.users'))

@bp.route('/users/<int:id>/reset_password', methods=['POST'])
@login_required
def reset_password(id):
    if g.user['role'] != 'admin':
        return redirect(url_for('index'))

    user = get_user_by_id(id)
    if not user:
        abort(404)

    new_password = ''.join(random.choices(string.digits, k=8))
    hashed_password = generate_password_hash(new_password)
    db = get_db()
    db.execute('UPDATE user SET password = ? WHERE id = ?', (hashed_password, id))
    db.commit()

    # Gửi new_password cho người dùng qua email hoặc phương thức an toàn
    flash(f'Mật khẩu mới là: {new_password}')  # XÓA BỎ trong production
    return redirect(url_for('admin.users'))

@bp.route('/users/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update_user(id):
    if g.user['role'] != 'admin':
        return redirect(url_for('index'))

    user = get_user_by_id(id)
    if not user:
        abort(404)

    if request.method == 'POST':
        username = request.form['username']
        role = request.form['role']
        # ... (lấy các dữ liệu khác từ form)

        db = get_db()
        error = None

        if not username:
            error = 'Username is required.'
        # ... (kiểm tra các trường dữ liệu khác)

        if error is None:
            try:
                db.execute(
                    'UPDATE user SET username = ?, role = ? WHERE id = ?',
                    (username, role, id)  # Cập nhật các trường dữ liệu khác
                )
                db.commit()
            except db.IntegrityError:
                error = f"User {username} is already registered."
            else:
                return redirect(url_for('admin.users'))

        flash(error)

    return render_template('admin/update_user.html', user=user)

@bp.route('/users/<int:id>/delete', methods=['POST'])
@login_required
def delete_user(id):
    if g.user['role'] != 'admin':
        return redirect(url_for('index'))

    user = get_user_by_id(id)
    if not user:
        abort(404)

    db = get_db()
    try:
        db.execute('DELETE FROM user WHERE id = ?', (id,))
        db.commit()
    except Exception as e:
        logging.error(f"Lỗi khi xóa người dùng (ID: {id}): {e}")
        flash(f"Lỗi khi xóa người dùng.")
        db.rollback()
    return redirect(url_for('admin.users'))

@bp.route('/dashboard')
@login_required
def dashboard():
    if g.user['role'] != 'admin':
        return redirect(url_for('index'))

    db = get_db()
    
    # Tổng số công việc
    total_tasks = db.execute('SELECT COUNT(*) as count FROM task').fetchone()['count']
    
    # Tổng số người dùng
    total_users = db.execute('SELECT COUNT(*) as count FROM user').fetchone()['count']
    
    # Số công việc đang thực hiện
    tasks_in_progress = db.execute(
        'SELECT COUNT(*) as count FROM task WHERE status = ?',
        ('in-progress',)
    ).fetchone()['count']
    
    # Công việc gần đây
    recent_tasks = db.execute(
        'SELECT t.id, t.title, t.created, u.username'
        ' FROM task t JOIN user u ON t.assigned_to = u.id'
        ' ORDER BY created DESC LIMIT 5'
    ).fetchall()
    
    # Top người dùng
    top_users = db.execute(
        'SELECT u.username, COUNT(*) as task_count'
        ' FROM task t JOIN user u ON t.assigned_to = u.id'
        ' GROUP BY u.id'
        ' ORDER BY task_count DESC LIMIT 5'
    ).fetchall()

    return render_template('admin/dashboard.html',
        total_tasks=total_tasks,
        total_users=total_users,
        tasks_in_progress=tasks_in_progress,
        recent_tasks=recent_tasks,
        top_users=top_users
    )

@bp.route('/options')
@login_required
def options():
    if g.user['role'] != 'admin':
        return redirect(url_for('index'))
    return render_template('admin/option.html')