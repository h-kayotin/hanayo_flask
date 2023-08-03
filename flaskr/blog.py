"""
blog - 工单展示和编辑

Author: hanayo
Date： 2023/7/28
"""

from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, session
)
from werkzeug.exceptions import abort

from flaskr.auth import login_required
from flaskr.db import get_db, admins
import datetime
import math

bp = Blueprint('blog', __name__)
status_dict = {
    "new": "新提交",
    "ongoing": "进行中",
    "closed": "已解决"
}
# 每页显示多少条
PAGE_SIZE = 5


def get_pages_data(is_admin, user_id, db, start_num, page_size, status=None):
    """
    用sql语句从数据库获取数据
    :param is_admin: 是否是管理员，布尔值
    :param user_id: 当前登录用户id
    :param db: 已连接的数据库对象
    :param start_num: 从第几条数据开始
    :param page_size: 每页显示多少条
    :param status: 对于状态的筛选，默认不筛选
    :return: 返回查询到的数据,和数据的总页数
    """
    # 这个sql语句用来获取要显示的一页数据
    sql_txt = """
        SELECT p.id, title, body, created, author_id, username, category, status, solution, owner, done
        FROM post p JOIN user u ON p.author_id = u.id
    """

    # 这个sql用来统计总共有多少数据
    sql_count = """
        SELECT count(*) as total_num FROM post p JOIN user u ON p.author_id = u.id
    """
    if status and is_admin:
        sql_txt += f"WHERE p.status = '{status}'"
        sql_count += f"WHERE p.status = '{status}'"

    if not is_admin:
        sql_txt += f' WHERE p.author_id = {user_id}'
        sql_count += f' WHERE p.author_id = {user_id}'
    sql_txt += ' ORDER BY created DESC'
    sql_txt += f' limit {start_num},{page_size}'
    posts = db.execute(sql_txt).fetchall()
    pages = db.execute(sql_count).fetchone()["total_num"]
    total_page_num = math.ceil(pages / page_size)
    return posts, total_page_num


@bp.route('/')
@login_required  # 该装饰器表示该页面需要登录，否则就转到登录页
def index(page=1, key_word=None):

    key_word = key_word
    # 定义从第几条开始
    num_s = (page-1) * PAGE_SIZE

    db = get_db()
    current_userid = session['user_id']
    is_admin = False
    if current_userid in admins:
        is_admin = True
    posts, total_page = get_pages_data(is_admin, current_userid, db, num_s, PAGE_SIZE, key_word)
    return render_template('blog/index.html', posts=posts, s_dict=status_dict,
                           is_admin=is_admin, key_word=key_word, total_page=total_page, page_num=page)


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
        'SELECT p.id, title, body, created, author_id, username, status, solution, owner, category'
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
        my_page_num = int(request.args["page"])
    except KeyError:
        key_word = None
        my_page_num = 0
    try:
        is_my_filter = request.args["filter"]
    except KeyError:
        is_my_filter = None
    try:
        my_page_num = int(request.args["page"])
    except KeyError:
        my_page_num = 0
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
    # 下面这个列表是用来显示编辑页面的工单类别
    types_list = [
        {"value": "outlook", "text": "邮箱", "selected": False},
        {"value": "PC", "text": "PC", "selected": False},
        {"value": "card", "text": "门禁卡", "selected": False},
        {"value": "other", "text": "其他", "selected": False}
    ]
    make_options(drop_down, post["status"])
    make_options(admins_list, post["owner"])
    make_options(types_list, post["category"])

    if request.method == 'POST':
        title = request.form['title']
        category = request.form.get('category')
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

        if status == "new" and owner is None:
            error = '错误：请选择一个负责人'

        if not title:
            error = '标题不能为空'

        if error is not None:
            flash(error)
        else:
            sql_text = f"""
                UPDATE post SET title = "{title}", body = "{body}", status = "{status}",
                solution = "{solution}", owner = "{owner}", category = "{category}"
            """
            if done:
                sql_text += f", done = '{done}'"
            sql_text += f" WHERE id = {id}"
            # print(sql_text)
            db = get_db()
            db.execute(sql_text)
            db.commit()
            if key_word:
                return index(page=my_page_num, key_word=status)
                # return redirect(url_for('blog.filter_display', status=key_word, page=my_page_num))
            elif is_my_filter:
                return redirect(url_for('blog.filter_my', owner=session['user_id']))
            elif my_page_num > 1:
                return index(page=my_page_num, key_word=None)
            else:
                return redirect(url_for('blog.index'))

    return render_template('blog/update.html', post=post, drop_down=drop_down, admins=admins_list,
                           types_list=types_list)


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
def filter_display(status, page=0):
    db = get_db()
    is_admin = True
    current_userid = session['user_id']
    if current_userid not in admins:
        is_admin = False
    key_word = status
    posts, total_page = get_pages_data(is_admin, current_userid, db, page, PAGE_SIZE, status=status)

    return render_template('blog/index.html', posts=posts, s_dict=status_dict, is_admin=is_admin,
                           key_word=key_word, total_page=total_page, page_num=1)


@bp.route('/<page>')
@login_required
def pre_page(page):
    """进行翻页"""
    pre_page_num = int(page)
    if pre_page_num > 0:
        return index(page=pre_page_num)
    else:
        return index()


@bp.route('/<page>/<status>')
@login_required
def pre_page_filter(page, status):
    """对于筛选后的结果进行翻页"""
    pre_page_num = int(page)
    # print(f"当前页码是{page}，筛选项目是{status}")
    if pre_page_num > 0:
        return index(page=pre_page_num, key_word=status)
    else:
        return index(key_word=status)


@bp.route('/my/<owner>')
@login_required
def filter_my(owner, page=0):
    admin_id = int(owner)
    sql_txt = f"""
        SELECT p.id, title, body, created, author_id, username, category, status, solution, owner, done
        FROM post p JOIN user u ON p.author_id = u.id
        WHERE p.owner = (SELECT username FROM user
        WHERE id = {admin_id}) and status = "ongoing"
        ORDER BY created DESC
    """
    db = get_db()
    posts = db.execute(sql_txt).fetchall()
    total_page = 0
    return render_template('blog/index.html', posts=posts, s_dict=status_dict,
                           is_admin=True, key_word=None, total_page=total_page, page_num=page,
                           filter="my")
