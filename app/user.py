import requests
from flask import Blueprint, render_template, g, request, flash, redirect, url_for, current_app
from werkzeug.security import generate_password_hash
from app.auth import login_required
from app.db import get_db
import random
import os
from werkzeug.utils import secure_filename

bp = Blueprint('user', __name__, url_prefix='/user')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def generate_avatar_url(username):
    """Tạo URL avatar ngẫu nhiên từ API"""
    random_number = random.randint(1, 1000)
    return f"https://avatar-placeholder.iran.liara.run/public/{username}?random={random_number}"

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/profile', methods=('GET', 'POST'))
@login_required
def profile():
    if request.method == 'POST':
        action = request.form.get('action')
        db = get_db()
        
        if action == 'update_avatar':
            if 'avatar_type' in request.form:
                avatar_type = request.form['avatar_type']
                
                if avatar_type == 'generated':
                    # Tạo avatar từ API như cũ
                    new_avatar = generate_avatar_url(g.user['username'])
                    
                elif avatar_type == 'upload':
                    # Xử lý upload file
                    if 'file' not in request.files:
                        flash('Không có file nào được chọn')
                        return redirect(request.url)
                    
                    file = request.files['file']
                    if file.filename == '':
                        flash('Không có file nào được chọn')
                        return redirect(request.url)
                    
                    if file and allowed_file(file.filename):
                        # Xóa avatar cũ nếu có
                        if g.user['avatar'] and '/static/uploads/' in g.user['avatar']:
                            old_avatar = os.path.join(
                                current_app.root_path,
                                'static',
                                g.user['avatar'].split('/static/')[1]
                            )
                            if os.path.exists(old_avatar):
                                os.remove(old_avatar)
                        
                        # Lưu file mới
                        filename = secure_filename(file.filename)
                        # Thêm username vào tên file để tránh trùng lặp
                        filename = f"{g.user['username']}_{filename}"
                        file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                        new_avatar = url_for('static', filename=f'uploads/{filename}')
                    else:
                        flash('File không hợp lệ. Chỉ chấp nhận ảnh định dạng png, jpg, jpeg, gif')
                        return redirect(request.url)
                
                # Cập nhật avatar trong database
                db.execute(
                    'UPDATE user SET avatar = ? WHERE id = ?',
                    (new_avatar, g.user['id'])
                )
                db.commit()
                flash('Avatar đã được cập nhật')
        
        elif action == 'update_profile':
            username = request.form['username']
            error = None

            if not username:
                error = 'Username is required.'
            
            if error is None:
                try:
                    db.execute(
                        'UPDATE user SET username = ? WHERE id = ?',
                        (username, g.user['id'])
                    )
                    db.commit()
                    flash('Profile đã được cập nhật')
                    return redirect(url_for('user.profile'))
                except db.IntegrityError:
                    error = f"User {username} is already registered."
            
            flash(error)

    # Lấy thông tin user mới nhất
    user = get_db().execute(
        'SELECT * FROM user WHERE id = ?', (g.user['id'],)
    ).fetchone()
    
    # Chuyển đổi user thành dict để dễ thao tác
    user_dict = dict(user)
    
    # Nếu user chưa có avatar hoặc avatar là None
    if 'avatar' not in user_dict or user_dict['avatar'] is None:
        avatar_url = generate_avatar_url(user_dict['username'])
        db = get_db()
        db.execute(
            'UPDATE user SET avatar = ? WHERE id = ?',
            (avatar_url, user_dict['id'])
        )
        db.commit()
        user_dict['avatar'] = avatar_url

    return render_template('user/profile.html', user=user_dict) 