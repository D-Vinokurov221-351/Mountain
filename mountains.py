import io
from flask import render_template, request, redirect, url_for, flash, Blueprint, send_file
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from app import db
from check_user import CheckUser
from functools import wraps
import mysql.connector
import math

bp_mountains = Blueprint('mountains', __name__, url_prefix='/mountains')

@bp_mountains.route('/show')
@login_required
def show_mountains():
    search_query = request.args.get('search', '')

    query = '''
        SELECT Mountains.*, 
               COUNT(DISTINCT Ascents.id) AS climb_count,
               COUNT(DISTINCT Ascent_Climbers.climber_id) AS climber_count
        FROM Mountains
        LEFT JOIN Ascents ON Ascents.mountain_id = Mountains.id
        LEFT JOIN Ascent_Climbers ON Ascent_Climbers.ascent_id = Ascents.id
        GROUP BY Mountains.id
    '''

    if search_query:
        query += '''
            HAVING Mountains.name LIKE %s OR 
                   Mountains.country LIKE %s OR 
                   Mountains.region LIKE %s
        '''
        search_value = f'%{search_query}%'
        cursor = db.connection().cursor(named_tuple=True)
        cursor.execute(query, (search_value, search_value, search_value))
    else:
        cursor = db.connection().cursor(named_tuple=True)
        cursor.execute(query)

    mountains = cursor.fetchall()
    cursor.close()

    return render_template('mountains/show.html', mountains=mountains)


@bp_mountains.route('/mountains/show_groups/<int:mountain_id>')
def show_groups(mountain_id):
    # Запрос для получения информации о горе и связанных восхождениях
    query = '''
        SELECT *
        FROM Mountains
        WHERE Mountains.id = %s
    '''

    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(query, (mountain_id,))
    
    mountain = cursor.fetchone()
    
    # Запрос для получения всех восхождений на эту гору
    ascents_query = '''
        SELECT group_name, start_date, end_date 
        FROM Ascents 
        WHERE mountain_id = %s
    '''
    
    cursor.execute(ascents_query, (mountain_id,))
    ascents = cursor.fetchall()
    
    cursor.close()

    if mountain is None:
        flash('Гора не найдена!', 'danger')
        return redirect(url_for('mountains.show_mountains'))

    return render_template('mountains/show_groups.html', mountain=mountain, ascents=ascents)


@bp_mountains.route('/mountains/edit/<int:mountain_id>', methods=['GET', 'POST'])
@login_required
def edit_mountain(mountain_id):

    if request.method == 'POST':
        mountain_query = '''
            SELECT * FROM Mountains WHERE id = %s
        '''
        cursor = db.connection().cursor(named_tuple=True)
        cursor.execute(mountain_query, (mountain_id,))
        mountain = cursor.fetchone()

        if mountain is None:
            flash('Гора не найдена!', 'danger')
            return redirect(url_for('mountains.show_mountains'))

        # Обработка формы редактирования
        name = request.form['name']
        height = request.form['height']
        country = request.form['country']

        # Обновление данных о горе
        update_query = '''
            UPDATE Mountains 
            SET name = %s, height = %s, country = %s 
            WHERE id = %s
        '''
        cursor = db.connection().cursor(named_tuple=True)
        cursor.execute(update_query, (name, height, country, mountain_id))
        db.connection().commit()
        cursor.close()
        flash(f'Данные горы {name} успешно обновлены!', 'success')

    # Получение информации о горе и проверка наличия восхождений
    mountain_query = '''
        SELECT * FROM Mountains WHERE id = %s
    '''
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(mountain_query, (mountain_id,))
    mountain = cursor.fetchone()
    cursor.close()

    ascent_query = '''
        SELECT * FROM Ascents WHERE mountain_id = %s
    '''
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(ascent_query, (mountain_id,))
    ascents = cursor.fetchall()

    has_ascent = len(ascents) > 0

    # Закрытие курсора и соединения
    cursor.close()

    return render_template('mountains/edit.html', mountain=mountain, has_ascent=has_ascent, ascents=ascents)

@bp_mountains.route('/delete/<int:mountain_id>', methods=['POST'])
@login_required
def delete_mountain(mountain_id):
    try:
        query = '''
            DELETE FROM Mountains WHERE id = %s
        '''
        cursor = db.connection().cursor(named_tuple=True)
        cursor.execute(query, (mountain_id,))
        db.connection().commit()
        flash(f'Гора с ID {mountain_id} успешно удалена.', 'success')
        cursor.close()
    except mysql.connector.errors.DatabaseError:
        db.connection().rollback()
        flash(f'При удалении горы произошла ошибка.', 'danger')
    
    return redirect(url_for('mountains.show_mountains'))  # Перенаправляем на страницу со списком гор

@bp_mountains.route('/add', methods=['GET', 'POST'])
@login_required
def add_mountain():
    if request.method == 'POST':
        name = request.form['name']
        height = request.form['height']
        country = request.form['country']
        region = request.form.get('region', '')  # Если регион не обязателен

        # Выполнение SQL-запроса для добавления новой вершины
        query = '''
            INSERT INTO Mountains (name, height, country, region)
            VALUES (%s, %s, %s, %s)
        '''
        cursor = db.connection().cursor()
        try:
            cursor.execute(query, (name, height, country, region))
            db.connection().commit()  # Сохраняем изменения
            flash('Вершина успешно добавлена!', 'success')
            return redirect(url_for('mountains.show_mountains'))  # Перенаправляем на страницу со списком гор
        except Exception as e:
            db.connection().rollback()  # Откат изменений в случае ошибки
            flash('Ошибка при добавлении вершины: ' + str(e), 'danger')
        finally:
            cursor.close()

    return render_template('mountains/create.html')

@bp_mountains.route('/show')
@login_required
def show_ascents():
    search_query = request.args.get('search', '')

    query = '''
        SELECT Mountains.*, 
               COUNT(DISTINCT Ascents.id) AS climb_count,
               COUNT(DISTINCT Ascent_Climbers.climber_id) AS climber_count
        FROM Mountains
        LEFT JOIN Ascents ON Ascents.mountain_id = Mountains.id
        LEFT JOIN Ascent_Climbers ON Ascent_Climbers.ascent_id = Ascents.id
        GROUP BY Mountains.id
    '''

    if search_query:
        query += '''
            HAVING Mountains.name LIKE %s OR 
                   Mountains.country LIKE %s OR 
                   Mountains.region LIKE %s
        '''
        search_value = f'%{search_query}%'
        cursor = db.connection().cursor(named_tuple=True)
        cursor.execute(query, (search_value, search_value, search_value))
    else:
        cursor = db.connection().cursor(named_tuple=True)
        cursor.execute(query)

    mountains = cursor.fetchall()
    cursor.close()

    return render_template('mountains/show.html', mountains=mountains)

