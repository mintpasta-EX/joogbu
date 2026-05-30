import os
from flask import Flask, request, redirect, render_template, session
import sqlite3
from datetime import datetime

base_dir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(base_dir, 'templates')

app = Flask(__name__, template_folder=template_dir)
app.secret_key = '12345'


def get_db():
    conn = sqlite3.connect('board.db')
    cursor = conn.cursor()
    return conn, cursor


def init_db():
    conn, cursor = get_db()
    # stat(능력치) 컬럼 추가됨!
    cursor.execute('''CREATE TABLE IF NOT EXISTS posts
                      (
                          id
                          INTEGER
                          PRIMARY
                          KEY
                          AUTOINCREMENT,
                          title
                          TEXT,
                          content
                          TEXT,
                          author
                          TEXT,
                          date
                          TEXT,
                          views
                          INTEGER
                          DEFAULT
                          0,
                          category
                          TEXT
                          DEFAULT
                          '기타',
                          price
                          INTEGER
                          DEFAULT
                          0,
                          stat
                          INTEGER
                          DEFAULT
                          0
                      )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS users
                      (
                          id
                          INTEGER
                          PRIMARY
                          KEY
                          AUTOINCREMENT,
                          username
                          TEXT,
                          password
                          TEXT,
                          role
                          TEXT
                          DEFAULT
                          'user'
                      )''')

    cursor.execute('SELECT COUNT(*) FROM users')
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users(username, password, role) VALUES(?,?,?)", ('admin', '1234', 'admin'))
    conn.commit()
    conn.close()


init_db()


@app.route('/')
def index():
    if 'username' not in session: return redirect('/login/')
    conn, cursor = get_db()

    cursor.execute('SELECT COUNT(*) FROM posts')
    count = cursor.fetchone()[0]

    keyword = request.args.get('keyword', '')
    min_stat = request.args.get('min_stat', '0')
    category_filter = request.args.get('category', '전체')  # 카테고리 값 받아오기!

    if not min_stat.isdigit() or min_stat == '': min_stat = '0'

    # 💡 3단 콤보 검색 쿼리 만들기
    query = 'SELECT * FROM posts WHERE stat >= ?'
    params = [int(min_stat)]

    if keyword:
        query += ' AND title LIKE ?'
        params.append('%' + keyword + '%')

    if category_filter != '전체':
        query += ' AND category = ?'
        params.append(category_filter)

    query += ' ORDER BY id DESC'

    cursor.execute(query, tuple(params))
    posts = cursor.fetchall()
    conn.close()

    searchResult = ''
    if keyword and len(posts) == 0:
        searchResult = f'<p style="color: #ff4757; text-align: center;">"{keyword}" 검색 결과가 없습니다.</p>'

    postList = ''
    for post in posts:
        post_id, title, _, author, date, _, category, price, stat = post

        emoji = "💎 기타"
        if category == "무기":
            emoji = "🗡️ 무기"
        elif category == "방어구":
            emoji = "🛡️ 방어구"
        elif category == "소모품":
            emoji = "🧪 소모품"

        css_class = ""
        display_title = title
        if '[rare]' in title:
            css_class = "item-rare"; display_title = title.replace('[rare]', '[희귀] ')
        elif '[epic]' in title:
            css_class = "item-epic"; display_title = title.replace('[epic]', '[영웅] ')
        elif '[legendary]' in title:
            css_class = "item-legendary"; display_title = title.replace('[legendary]', '[전설] ')

        fmt_price = f"{price:,}" if isinstance(price, int) else str(price)

        postList += f'''
        <tr>
            <td style="padding: 15px 10px; border-bottom: 1px solid #333;">{post_id}</td>
            <td style="padding: 15px 10px; color: #aaa; border-bottom: 1px solid #333;">{emoji}</td>
            <td style="padding: 15px 10px; text-align: left; padding-left: 20px; border-bottom: 1px solid #333;">
                <a href="/detail/{post_id}/" class="item-name {css_class}" style="text-decoration:none;">{display_title}</a>
            </td>
            <td style="padding: 15px 10px; color: #4cd137; font-weight: bold; border-bottom: 1px solid #333;">+{stat}</td>
            <td style="padding: 15px 10px; color: #ffd700; font-weight: bold; border-bottom: 1px solid #333;">{fmt_price} G</td>
            <td style="padding: 15px 10px; color: #888; font-size: 10pt; border-bottom: 1px solid #333;">{date}</td>
        </tr>
        '''
    # 리턴 줄에 category_filter 변수도 HTML로 넘겨주도록 추가됨!
    return render_template('index.html', count=count, keyword=keyword, min_stat=min_stat,
                           category_filter=category_filter, postList=postList, searchResult=searchResult)


@app.route('/detail/<id>/')
def detail(id):
    conn, cursor = get_db()
    cursor.execute('UPDATE posts SET views = views + 1 WHERE id = ?', (id,))
    conn.commit()
    cursor.execute('SELECT * FROM posts WHERE id = ?', (id,))
    post = cursor.fetchone()
    conn.close()
    if not post: return redirect('/')
    return render_template('detail.html', post=post)


@app.route('/create/', methods=['GET', 'POST'])
def create():
    if 'username' not in session: return redirect('/login/')
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        author = request.form['author']
        price = request.form['price']
        category = request.form['category']
        stat = request.form.get('stat', 0)
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        conn, cursor = get_db()
        cursor.execute('''INSERT INTO posts(title, content, author, date, category, price, stat)
                          VALUES (?, ?, ?, ?, ?, ?, ?)''',
                       (title, content, author, date, category, price, stat))
        conn.commit()
        conn.close()
        return redirect('/')
    return render_template('create.html')


# (이하 update, delete, login, register, admin 등 나머지 라우트는 기존 app.py 코드 그대로 유지하시면 됩니다!)

@app.route('/update/<id>/', methods=['GET','POST'])
def update(id):
    conn, cursor = get_db()
    if 'username' not in session:
        return redirect('/login/')
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        author = request.form['author']
        price = request.form['price']

        cursor.execute('UPDATE posts SET title=?, content=?, author=?, price=? WHERE id = ?',
            (title, content, author, price, id))
        conn.commit()
        conn.close()
        return redirect(f'/detail/{id}/')

    cursor.execute('SELECT * FROM posts WHERE id = ?', (id,))
    post = cursor.fetchone()
    conn.close()
    return render_template('update.html', post=post, id=id)

@app.route('/delete/<id>/')
def delete(id):
    conn, cursor = get_db()
    cursor.execute('''DELETE FROM posts WHERE id = ?''', (id,))
    conn.commit()

    cursor.execute('SELECT id FROM posts ORDER BY id DESC LIMIT 1')
    first = cursor.fetchone()
    conn.close()
    if 'username' not in session:
        return redirect('/login/')
    if first:
        return redirect('/')
    else:
        return redirect('/empty/')

@app.route('/register/', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn, cursor = get_db()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        if user:
            conn.close()
            return render_template('register.html',error='이미 존재하는 아이디 입니다',success='')
        cursor.execute('INSERT INTO users(username,password) VALUES(?,?)', (username,password))
        conn.commit()
        conn.close()
        session['username'] = username
        return render_template('register.html',error='',success='길드 가입을 환영합니다!')
    return render_template('register.html',error='',success='')

@app.route('/login/', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn, cursor = get_db()
        cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username,password))
        user = cursor.fetchone()
        conn.close()
        if user:
            session['username'] = user[1]
            session['role'] = user[3]
            if user[3] == 'admin':
                return redirect('/admin/')
            else:
                return redirect('/')
        else:
            return render_template('login.html',error='아이디 또는 비밀번호가 틀렸습니다.')
    return render_template('login.html',error='')

@app.route('/logout/')
def logout():
    session.pop('username', None)
    return redirect('/')

@app.route('/empty/')
def empty():
    return render_template('empty.html')

@app.route('/admin/')
def admin():
    if 'username' not in session:
        return redirect('/login/')
    if session.get('role') != 'admin':
        return redirect('/')

    conn, cursor = get_db()
    cursor.execute('SELECT * FROM users')
    users = cursor.fetchall()
    cursor.execute('SELECT * FROM posts ORDER BY id DESC')
    posts= cursor.fetchall()
    cursor.execute('SELECT COUNT(*) FROM users')
    userCount = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM posts')
    postsCount = cursor.fetchone()[0]
    conn.close()
    return render_template('admin.html',userCount=userCount,postsCount=postsCount, users=users, posts=posts)

@app.route('/admin/delete/<id>/')
def admin_delete(id):
    if session.get('role') != 'admin':
        return redirect('/')
    conn, cursor = get_db()
    cursor.execute('DELETE FROM users WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect('/admin/')

@app.route('/admin/role/<id>/')
def admin_role(id):
    if session.get('role') != 'admin':
        return redirect('/')
    conn, cursor = get_db()
    cursor.execute('SELECT role FROM users WHERE id = ?', (id,))
    user = cursor.fetchone()
    if user[0] == 'user':
        newRole = 'admin'
    else:
        newRole = 'user'
    cursor.execute('UPDATE users SET role=? WHERE id=?', (newRole, id))
    conn.commit()
    conn.close()
    return redirect('/admin/')

@app.route('/admin/post/delete/<id>/')
def admin_post_delete(id):
    if session.get('role') != 'admin':
        return redirect('/')
    conn, cursor = get_db()
    cursor.execute('DELETE FROM posts WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect('/admin/')

#if __name__ == '__main__':
    #app.run(debug=True)
