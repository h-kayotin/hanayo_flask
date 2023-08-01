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
status_dict = {
    "new": "新提交",
    "ongoing": "进行中",
    "closed": "已解决"
}
# 这里设置管理员的ID，只有管理员有编辑权限
admins = {1, 2, 3}


@bp.route('/')
@login_required  # 该装饰器表示该页面需要登录，否则就转到登录页
def index():

    db = get_db()
    current_userid = session['user_id']
    key_word = None
    # 如果登录的不是管理员，那么就只显示登录用户提交的工单
    sql_txt = """
        SELECT p.id, title, body, created, author_id, username, category, status, solution, owner, done
        FROM post p JOIN user u ON p.author_id = u.id
    """
    if current_userid not in admins:
        sql_txt += f' WHERE p.author_id = {current_userid}'
        is_admin = False
    else:
        is_admin = True
    sql_txt += ' ORDER BY created DESC'
    posts = db.execute(sql_txt).fetchall()
    return render_template('blog/index.html', posts=posts, s_dict=status_dict, is_admin=is_admin, key=key_word)


@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        category = request.form.get('category')
        status = "new"
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
        'SELECT p.id, title, body, created, author_id, username,status, solution, owner'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' WHERE p.id = ?',
        (id,)
    ).fetchone()

    if post is None:
        abort(404, f"Post id {id} doesn't exist.")

    # if check_author and post['author_id'] != g.user['id']:
    #     abort(403)
    # 权限修改为管理员可以编辑所有页面
    if check_author and g.user['id'] not in admins:
        abort(403)

    return post


def make_options(option_list, post_value):
    """生成下拉框"""
    for option in option_list:
        if option["value"] == post_value:
            option["selected"] = True


@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    # 如果请求中带有key参数，那么保存后返回之前的筛选
    # print("来源url是", request.url)
    try:
        key_word = request.args["key"]
    except KeyError:
        key_word = None
    post = get_post(id)
    # 以下两个列表用来生成编辑页面的下拉菜单
    drop_down = [
        {"value": "new", "text": "新提交", "selected": False},
        {"value": "ongoing", "text": "进行中", "selected": False},
        {"value": "closed", "text": "已解决", "selected": False},
    ]
    # 此处可选择的工程师，他们的id包含在admins里
    admins_list = [
        {"value": "jianghai", "text": "江海", "selected": False},
        {"value": "liushengwu", "text": "陈san", "selected": False},
        {"value": "chenhaomin", "text": "刘san", "selected": False},
    ]
    make_options(drop_down, post["status"])
    make_options(admins_list, post["owner"])
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        status = request.form.get('status')
        solution = request.form['solution']
        owner = request.form.get('owner')
        error = None
        done = None

        # 如果已解决，更新解决时间
        if status == "closed":
            done = datetime.datetime.now()
        # 如果状态是新的，但是选择了负责人，那么状态就是进行中
        if status == "new" and owner is not None:
            status = "ongoing"

        if not title:
            error = '标题不能为空'

        if error is not None:
            flash(error)
        else:
            sql_text = f"""
                UPDATE post SET title = "{title}", body = "{body}", status = "{status}",
                solution = "{solution}", owner = "{owner}"
            """
            if done:
                sql_text += f", done = '{done}'"
            sql_text += f" WHERE id = {id}"
            # print(sql_text)
            db = get_db()
            db.execute(sql_text)
            db.commit()
            if key_word:
                return redirect(url_for('blog.filter_display', status=key_word))
            else:
                return redirect(url_for('blog.index'))

    return render_template('blog/update.html', post=post, drop_down=drop_down, admins=admins_list)


@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_post(id)
    db = get_db()
    db.execute('DELETE FROM post WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('blog.index'))


@bp.route('/filter_display/<status>')
@login_required
def filter_display(status):
    db = get_db()
    is_admin = True
    current_userid = session['user_id']
    if current_userid not in admins:
        is_admin = False
    key_word = status
    sql_txt = f"""
        SELECT p.id, title, body, created, author_id, username, category, status, solution, owner, done
        FROM post p JOIN user u ON p.author_id = u.id
        WHERE p.status = "{key_word}"
        ORDER BY created DESC
    """
    posts = db.execute(sql_txt).fetchall()
    return render_template('blog/index.html', posts=posts, s_dict=status_dict, is_admin=is_admin, key=key_word)
