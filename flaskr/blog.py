"""
blog - 

Author: hanayo
Date： 2023/7/28
"""

from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, session
)
from werkzeug.exceptions import abort

from flaskr.auth import login_required
from flaskr.db import get_db
import datetime

bp = Blueprint('blog', __name__)


@bp.route('/')
@login_required  # 该装饰器表示该页面需要登录，否则就转到登录页
def index():
    admins = {1, 2, 3}
    db = get_db()
    current_userid = session['user_id']
    # 如果登录的不是管理员，那么就只显示登录用户提交的工单
    sql_txt = """
        SELECT p.id, title, body, created, author_id, username, category, status
        FROM post p JOIN user u ON p.author_id = u.id
    """
    if current_userid not in admins:
        sql_txt += f' WHERE p.author_id = {current_userid}'
    sql_txt += ' ORDER BY created DESC'
    posts = db.execute(sql_txt).fetchall()
    return render_template('blog/index.html', posts=posts)


@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        category = request.form.get('category')
        status = "新提交"
        created = datetime.datetime.now()
        error = None

        if not title:
            error = '请填写标题'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'INSERT INTO post (title, body, author_id, category, status, created)'
                ' VALUES (?, ?, ?, ?, ?, ?)',
                (title, body, g.user['id'], category, status, created)
            )
            db.commit()
            return redirect(url_for('blog.index'))

    return render_template('blog/create.html')


def get_post(id, check_author=True):
    post = get_db().execute(
        'SELECT p.id, title, body, created, author_id, username'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' WHERE p.id = ?',
        (id,)
    ).fetchone()

    if post is None:
        abort(404, f"Post id {id} doesn't exist.")

    if check_author and post['author_id'] != g.user['id']:
        abort(403)

    return post


@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    post = get_post(id)

    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE post SET title = ?, body = ?'
                ' WHERE id = ?',
                (title, body, id)
            )
            db.commit()
            return redirect(url_for('blog.index'))

    return render_template('blog/update.html', post=post)


@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_post(id)
    db = get_db()
    db.execute('DELETE FROM post WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('blog.index'))

