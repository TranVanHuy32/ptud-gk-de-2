from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort
from app.auth import login_required
from app.db import get_db

bp = Blueprint('category', __name__, url_prefix='/category')

@bp.route('/')
@login_required
def index():
    db = get_db()
    categories = db.execute(
        'SELECT c.*, COUNT(t.id) as task_count'
        ' FROM category c'
        ' LEFT JOIN task t ON c.id = t.category_id'
        ' WHERE c.created_by = ?'
        ' GROUP BY c.id',
        (g.user['id'],)
    ).fetchall()
    return render_template('category/index.html', categories=categories)

@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    category = get_category(id)

    if request.method == 'POST':
        name = request.form['name']
        error = None

        if not name:
            error = 'Name is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE category SET name = ?'
                ' WHERE id = ?',
                (name, id)
            )
            db.commit()
            return redirect(url_for('category.index'))

    return render_template('category/update.html', category=category)

def get_category(id):
    category = get_db().execute(
        'SELECT c.*, COUNT(t.id) as task_count'
        ' FROM category c'
        ' LEFT JOIN task t ON c.id = t.category_id'
        ' WHERE c.id = ? AND c.created_by = ?'
        ' GROUP BY c.id',
        (id, g.user['id'])
    ).fetchone()

    if category is None:
        abort(404, f"Category id {id} doesn't exist.")

    return category 