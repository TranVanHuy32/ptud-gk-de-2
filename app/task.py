from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, jsonify, current_app
)
from werkzeug.exceptions import abort
from datetime import datetime
from app.auth import login_required
from app.db import get_db

bp = Blueprint('task', __name__)

@bp.route('/')
def index():
    db = get_db()
    if g.user and g.user['role'] == 'admin':
        # Admin xem tất cả task
        tasks = db.execute(
            'SELECT t.id, t.title, t.description, t.status, t.created, t.finished,'
            ' t.assigned_to, t.created_by, t.category_id,'
            ' u1.username as assigned_name,'
            ' u2.username as creator_name,'
            ' c.name as category_name, c.color as category_color'
            ' FROM task t'
            ' JOIN user u1 ON t.assigned_to = u1.id'
            ' JOIN user u2 ON t.created_by = u2.id'
            ' LEFT JOIN category c ON t.category_id = c.id'
            ' ORDER BY created DESC'
        ).fetchall()
    elif g.user:
        # User chỉ xem task liên quan đến mình (được assign hoặc tạo ra)
        tasks = db.execute(
            'SELECT t.id, t.title, t.description, t.status, t.created, t.finished,'
            ' t.assigned_to, t.created_by, t.category_id,'
            ' u1.username as assigned_name,'
            ' u2.username as creator_name,'
            ' c.name as category_name, c.color as category_color'
            ' FROM task t'
            ' JOIN user u1 ON t.assigned_to = u1.id'
            ' JOIN user u2 ON t.created_by = u2.id'
            ' LEFT JOIN category c ON t.category_id = c.id'
            ' WHERE t.assigned_to = ? OR t.created_by = ?'
            ' ORDER BY created DESC',
            (g.user['id'], g.user['id'])
        ).fetchall()
    else:
        tasks = []

    return render_template('task/index.html', tasks=tasks)

@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        assigned_to = request.form['assigned_to']
        category_id = request.form['category_id'] or None
        error = None

        if not title:
            error = 'Title is required.'

        if error is None:
            db = get_db()
            db.execute(
                'INSERT INTO task (title, description, status, created_by, assigned_to, category_id)'
                ' VALUES (?, ?, ?, ?, ?, ?)',
                (title, description, 'pending', g.user['id'], assigned_to, category_id)
            )
            db.commit()
            return redirect(url_for('task.index'))

        flash(error)

    # Lấy danh sách user và category để hiển thị trong form
    db = get_db()
    users = db.execute('SELECT id, username FROM user').fetchall()
    categories = db.execute(
        'SELECT * FROM category WHERE created_by = ?',
        (g.user['id'],)
    ).fetchall()
    return render_template('task/create.html', users=users, categories=categories)

@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    task = get_task(id)

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        status = request.form['status']
        error = None

        if not title:
            error = 'Title is required.'

        if error is None:
            db = get_db()
            if status == 'completed' and task['status'] != 'completed':
                # Nếu chuyển sang completed, cập nhật thời gian hoàn thành
                db.execute(
                    'UPDATE task SET title = ?, description = ?, status = ?, finished = CURRENT_TIMESTAMP'
                    ' WHERE id = ?',
                    (title, description, status, id)
                )
            elif status != 'completed':
                # Nếu chuyển từ completed sang trạng thái khác, xóa thời gian hoàn thành
                db.execute(
                    'UPDATE task SET title = ?, description = ?, status = ?, finished = NULL'
                    ' WHERE id = ?',
                    (title, description, status, id)
                )
            else:
                # Giữ nguyên thời gian hoàn thành nếu đã completed
                db.execute(
                    'UPDATE task SET title = ?, description = ?, status = ?'
                    ' WHERE id = ?',
                    (title, description, status, id)
                )
            db.commit()
            return redirect(url_for('task.index'))

        flash(error)

    return render_template('task/update.html', task=task)

@bp.route('/<int:id>/update_status', methods=['POST'])
@login_required
def update_status(id):
    task = get_task(id, check_author=False)
    
    # Cho phép người được assign, người tạo và admin cập nhật status
    if g.user['id'] != task['assigned_to'] and g.user['id'] != task['created_by'] and g.user['role'] != 'admin':
        abort(403)

    new_status = request.form.get('status')
    if new_status not in ['pending', 'in-progress', 'completed']:
        abort(400)

    db = get_db()
    try:
        if new_status == 'completed':
            db.execute(
                'UPDATE task SET status = ?, finished = CURRENT_TIMESTAMP'
                ' WHERE id = ?',
                (new_status, id)
            )
        else:
            db.execute(
                'UPDATE task SET status = ?, finished = NULL'
                ' WHERE id = ?',
                (new_status, id)
            )
        db.commit()
        return jsonify({
            'status': 'success',
            'new_status': new_status,
            'color': _get_status_color(new_status)
        })
    except:
        db.rollback()
        return jsonify({'status': 'error'}), 500

def get_task(id, check_author=True):
    task = get_db().execute(
        'SELECT t.id, title, description, status, created, finished, assigned_to,'
        ' created_by, u1.username as assigned_name, u2.username as creator_name'
        ' FROM task t JOIN user u1 ON t.assigned_to = u1.id'
        ' JOIN user u2 ON t.created_by = u2.id'
        ' WHERE t.id = ?',
        (id,)
    ).fetchone()

    if task is None:
        abort(404, f"Task id {id} doesn't exist.")

    if check_author and task['created_by'] != g.user['id'] and g.user['role'] != 'admin':
        abort(403)

    return task

@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_task(id)
    db = get_db()
    db.execute('DELETE FROM task WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('task.index'))

def _get_status_color(status):
    colors = {
        'pending': '#ffd700',
        'in-progress': '#1e90ff',
        'completed': '#32cd32'
    }
    return colors.get(status, '#666')

# Đăng ký template global function
@bp.app_template_global('get_status_color')
def get_status_color(status):
    return _get_status_color(status) 