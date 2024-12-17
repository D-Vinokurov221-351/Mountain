from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from mysql_db import MySQL
import mysql.connector

app = Flask(__name__)

application = app

app.config.from_pyfile('config.py')

db = MySQL(app)

from auth import bp_auth, check_rights, init_login_manager
from mountains import bp_mountains
from ascents import bp_ascents

app.register_blueprint(bp_auth)
app.register_blueprint(bp_mountains)
app.register_blueprint(bp_ascents)

init_login_manager(app)

#@app.before_request
#def journal():
#    query = '''
#        INSERT INTO `journal` (path, user_id) VALUES (%s, %s)
#    '''
#    try:
#        cursor = db.connection().cursor(named_tuple=True)
#        cursor.execute(query, (request.path, getattr(current_user, "id", None)))
#        db.connection().commit()
#        cursor.close()
#    except mysql.connector.errors.DatabaseError:
#        db.connection().rollback()

def get_roles():
    query = 'SELECT * FROM Roles'
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(query)
    roles = cursor.fetchall()
    cursor.close()
    return roles


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/users/')
@login_required
def show_users():
    search_query = request.args.get('search', '')
    
    query = '''
        SELECT Climbers.*, Roles.role_name as role_name
        FROM Climbers
        LEFT JOIN Roles ON Roles.id = Climbers.role_id
    '''
    
    if search_query:
        query += '''
            WHERE Climbers.login LIKE %s OR Climbers.name LIKE %s
        '''
        search_value = f'%{search_query}%'
        cursor = db.connection().cursor(named_tuple=True)
        cursor.execute(query, (search_value, search_value))
    else:
        cursor = db.connection().cursor(named_tuple=True)
        cursor.execute(query)
    
    users = cursor.fetchall()
    cursor.close()
    
    return render_template('users/index.html', users=users)


@app.route('/users/create', methods=['POST', 'GET'])
@login_required
@check_rights('create')
def create():
    roles = get_roles()
    if request.method == 'POST':
        login = request.form['login']  # Обновлено на 'username'
        name = request.form['name']
        address = request.form['address']
        password = request.form['password']
        role_id = request.form['role_id']
        try:
            query = '''
                INSERT INTO Climbers (login, name, address, password_hash, role_id)
                VALUES (%s, %s, %s, SHA2(%s, 256), %s)
            '''
            cursor = db.connection().cursor(named_tuple=True)
            cursor.execute(query, (login, name, address, password, role_id))
            db.connection().commit()
            flash(f'Пользователь {login} успешно создан.', 'success')
            cursor.close()
        except mysql.connector.errors.DatabaseError:
            db.connection().rollback()
            flash(f'При создании пользователя произошла ошибка.', 'danger')
            return render_template('users/create.html', roles=roles)

    return render_template('users/create.html', roles=roles)


@app.route('/users/show/<int:user_id>', methods=['GET', 'POST'])
@check_rights('show')
def show_user(user_id):
    if request.method == 'POST':
        new_name = request.form['name']
        login = request.form['login']
        old_password = request.form['password_old']
        new_password = request.form['password']

        # Проверка старого пароля
        query = '''
            SELECT id FROM Climbers WHERE id=%s AND password_hash=SHA2(%s, 256)
        '''
        with db.connection().cursor() as cursor:
            cursor.execute(query, (user_id, old_password))
            user_exists = cursor.fetchone()  # Используем fetchone для получения одного результата

        # Проверка на пустой новый пароль и правильность старого пароля
        if new_password == "" or not user_exists:
            flash('Данные не обновлены! Проверьте правильность в полях паролей!', 'danger')
            return redirect(url_for('show_user', user_id=user_id))
        
        # Обновление данных пользователя
        update_query = '''
            UPDATE Climbers 
            SET name=%s, login=%s, password_hash=SHA2(%s, 256)
            WHERE id=%s
        '''
        with db.connection().cursor() as cursor:
            cursor.execute(update_query, (new_name, login, new_password, user_id))
            db.connection().commit()
        
        flash('Данные успешно обновлены!', 'success')
        return redirect(url_for('show_user', user_id=user_id))

    # Получение данных пользователя и его восхождений
    query_user = 'SELECT * FROM Climbers WHERE id=%s'
    query_ascents = '''
        SELECT a.start_date, a.end_date, m.name as mountain_name, a.group_name 
        FROM Ascents a
        JOIN Ascent_Climbers ac ON a.id = ac.ascent_id
        JOIN Mountains m ON a.mountain_id = m.id
        WHERE ac.climber_id = %s
    '''
    
    query_mountains_with_counts = '''
        SELECT 
            m.name AS mountain_name,
            COUNT(ac.climber_id) AS ascent_count
        FROM 
            Mountains m
        LEFT JOIN 
            Ascents a ON m.id = a.mountain_id
        LEFT JOIN 
            Ascent_Climbers ac ON a.id = ac.ascent_id AND ac.climber_id = %s
        GROUP BY 
            m.id
        ORDER BY 
            ascent_count DESC;
    '''

    with db.connection().cursor(named_tuple=True) as cursor:
        cursor.execute(query_user, (user_id,))
        user = cursor.fetchone()
        
        cursor.execute(query_ascents, (user_id,))
        ascents = cursor.fetchall()

        cursor.execute(query_mountains_with_counts, (user_id,))
        mountains_with_counts = cursor.fetchall()

    # Преобразуем данные пользователя в словарь
    user_data = {
        'id': user.id,
        'name': user.name,
        'address': user.address,
        'login': user.login,
        'ascents': ascents,  # Добавляем список восхождений
        'mountains_with_counts': mountains_with_counts  # Добавляем количество восхождений на горы
    }
    
    return render_template('users/show.html', user=user_data)


@app.route('/users/edit/<int:user_id>', methods=["POST", "GET"])
@login_required
@check_rights('edit')
def edit(user_id):
    roles = get_roles()  # Получаем список ролей для отображения в форме
    if request.method == 'POST':
        username = request.form['login']  # Обновлено на 'username'
        name = request.form['name']
        address = request.form['address']
        password = request.form['password']
        role_id = request.form['role_id']
        try:
            query = '''
                UPDATE Climbers 
                SET login = %s, name = %s, address = %s, password_hash=SHA2(%s,256), role_id = %s 
                WHERE id = %s
            '''
            cursor = db.connection().cursor(named_tuple=True)
            cursor.execute(query, (username, name, address, password, role_id, user_id))
            db.connection().commit()
            flash(f'Данные пользователя {name} успешно обновлены.', 'success')
            cursor.close()
        except mysql.connector.errors.DatabaseError:
            db.connection().rollback()
            flash(f'При обновлении пользователя произошла ошибка.', 'danger')
            return render_template('users/edit.html', user=user, roles=roles)

    query = '''
        SELECT Climbers.*
        FROM Climbers
        WHERE Climbers.id=%s
    '''
    with db.connection().cursor(named_tuple=True) as cursor:
        cursor.execute(query, (user_id,))
        user = cursor.fetchone()
    
    return render_template('users/edit.html', user=user, roles=roles)  # Передаем роли в шаблон


@app.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@check_rights('delete')
def delete(user_id):
    try:
        query = '''
            DELETE FROM Climbers WHERE id = %s
        '''
        cursor = db.connection().cursor(named_tuple=True)
        cursor.execute(query, (user_id,))
        db.connection().commit()
        flash(f'Пользователь с ID {user_id} успешно удален.', 'success')
        cursor.close()
    except mysql.connector.errors.DatabaseError:
        db.connection().rollback()
        flash(f'При удалении пользователя произошла ошибка.', 'danger')
    
    return redirect(url_for('show_users'))

