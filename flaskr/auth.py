"""
auth - 

Author: hanayo
Date： 2023/7/28
"""

import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash
import csv
from flaskr.db import get_db

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/register', methods=('GET', 'POST'))
def register():
    # # 以下代码确保注册页只有管理员能访问
    # try:
    #     current_userid = session['user_id']
    #     if not current_userid == 1:
    #         return redirect(url_for('blog.index'))
    # except KeyError:
    #     return redirect(url_for('auth.login'))
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
                    "INSERT INTO user (username, password) VALUES (?, ?)",
                    (username, generate_password_hash(password)),
                )
                db.commit()
            except db.IntegrityError:
                error = f"用户： {username} 已存在。"
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
        user = db.execute(
            'SELECT * FROM user WHERE username = ?', (username,)
        ).fetchone()

        if user is None:
            error = 'Incorrect username.'
        elif not check_password_hash(user['password'], password):
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
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id = ?', (user_id,)
        ).fetchone()


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view


UPLOAD_FOLDER = '/upload'
ALLOWED_EXTENSIONS = {'csv'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route('/input_users', methods=('GET', 'POST'))
def input_users():
    """选择excel，批量导入用户"""
    # 以下代码确保注册页只有管理员能访问
    try:
        current_userid = session['user_id']
        if not current_userid == 1:
            return redirect(url_for('blog.index'))
    except KeyError:
        return redirect(url_for('auth.login'))

    # 上传文件
    if request.method == 'POST':
        db = get_db()
        error = None
        # 检查是否有文件被选择
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']

        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('未选择文件')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            data = file.read().decode("utf-8-sig")
            reader = csv.reader(data.splitlines(), delimiter=',')
            for row in reader:
                user_name = row[0]
                user_pwd = row[1]
                try:
                    db.execute(
                        "INSERT INTO user (username, password) VALUES (?, ?)",
                        (user_name, generate_password_hash(user_pwd)),
                    )
                    db.commit()
                except db.IntegrityError:
                    error = f"用户： {user_name} 已存在。"
                    return f"导入失败，{error}<a href='register'>返回注册页</a>"
            return "<p>导入用户成功</p><a href='/'>回到首页</a>"

    return '''
    <!doctype html>
    <title>上传文件</title>
    <h1>上传文件</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=读取文件>
    </form>
    '''

    # return "<p>导入用户成功</p><a href='/'>回到首页</a>"

