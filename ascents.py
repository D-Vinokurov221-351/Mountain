import io
from flask import render_template, request, redirect, url_for, flash, Blueprint, send_file
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from app import db
from check_user import CheckUser
from functools import wraps
import mysql.connector
import math

bp_ascents = Blueprint('ascents', __name__, url_prefix='/ascents')

@bp_ascents.route('/show')
@login_required
def show_ascents():
    search_query = request.args.get('search', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    query = '''
        SELECT Ascents.*, 
               Mountains.name AS mountain_name,
               COUNT(DISTINCT Ascent_Climbers.climber_id) AS climber_count
        FROM Ascents
        LEFT JOIN Mountains ON Ascents.mountain_id = Mountains.id
        LEFT JOIN Ascent_Climbers ON Ascent_Climbers.ascent_id = Ascents.id
        GROUP BY Ascents.id
    '''

    conditions = []
    params = []

    if search_query:
        conditions.append('(Ascents.group_name LIKE %s OR Mountains.name LIKE %s)')
        search_value = f'%{search_query}%'
        params.extend([search_value, search_value])

    if start_date:
        conditions.append('Ascents.start_date >= %s')
        params.append(start_date)

    if end_date:
        conditions.append('Ascents.end_date <= %s')
        params.append(end_date)

    if conditions:
        query += ' HAVING ' + ' AND '.join(conditions)

    query += ' ORDER BY Ascents.start_date DESC'
    
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(query, params)
    ascents = cursor.fetchall()

    # Получаем альпинистов для каждого восхождения
    climbers_query = '''
        SELECT Climbers.name AS climber_name, Ascent_Climbers.ascent_id, Climbers.id AS climber_id
        FROM Ascent_Climbers
        JOIN Climbers ON Ascent_Climbers.climber_id = Climbers.id
        JOIN Ascents ON Ascents.id = Ascent_Climbers.ascent_id
        WHERE Ascents.start_date >= %s and Ascents.end_date <= %s
    '''
    
    cursor.execute(climbers_query, (start_date, end_date))
    climbers_data = cursor.fetchall()
    
    # Создаем словарь для группировки альпинистов по ID
    climbers_by_id = {}
    for climber in climbers_data:
        climber_id = climber.climber_id
        if climber_id not in climbers_by_id:
            climbers_by_id[climber_id] = {
                'name': climber.climber_name,
                'ascents': []
            }
        climbers_by_id[climber_id]['ascents'].append({
            'ascent_id': climber.ascent_id
        })

    cursor.close()

    return render_template('ascents/show.html', ascents=ascents, climbers_by_id=climbers_by_id, start_date=start_date, end_date=end_date)




@bp_ascents.route('/show/<int:ascent_id>/climbers')
@login_required
def show_ascent_details(ascent_id):

    query_mountain = '''
        SELECT Mountains.name
        FROM Ascents
        JOIN Mountains ON Ascents.mountain_id = Mountains.id
        WHERE Ascents.id = %s
    '''

    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(query_mountain, (ascent_id,))
    mountain = cursor.fetchone()

    query = '''
        SELECT Climbers.*, Mountains.name AS mountain_name
        FROM Ascent_Climbers
        JOIN Climbers ON Ascent_Climbers.climber_id = Climbers.id
        JOIN Ascents ON Ascent_Climbers.ascent_id = Ascents.id
        JOIN Mountains ON Ascents.mountain_id = Mountains.id
        WHERE Ascent_Climbers.ascent_id = %s
    '''
    
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(query, (ascent_id,))
    climbers = cursor.fetchall()
    cursor.close()

    return render_template('ascents/show_ascent_details.html', climbers=climbers, ascent_id=ascent_id, mountain=mountain)



@bp_ascents.route('/edit/<int:ascent_id>', methods=['GET'])
@login_required
def edit_ascent(ascent_id):
    search_query_c = request.args.get('search_c', '')
    search_query_nc = request.args.get('search_nc', '')

    query_mountain = '''
        SELECT Mountains.name
        FROM Ascents
        JOIN Mountains ON Ascents.mountain_id = Mountains.id
        WHERE Ascents.id = %s
    '''

    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(query_mountain, (ascent_id,))
    mountain = cursor.fetchone()

    query_climbers = '''
        SELECT Climbers.*
        FROM Ascent_Climbers
        JOIN Climbers ON Ascent_Climbers.climber_id = Climbers.id
        WHERE Ascent_Climbers.ascent_id = %s and (Climbers.login LIKE %s OR Climbers.name LIKE %s)
    '''
    search_value_c = f'%{search_query_c}%'
    
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(query_climbers, (ascent_id, search_value_c, search_query_c))
    climbers = cursor.fetchall()

    query_all_climbers = '''
        SELECT *
        FROM Climbers
        WHERE Climbers.login LIKE %s OR Climbers.name LIKE %s
    '''

    search_value_nc = f'%{search_query_nc}%'
    cursor.execute(query_all_climbers, (search_value_nc, search_value_nc))
    all_climbers = cursor.fetchall()
    cursor.close()

    climber_ids = {climber.id for climber in climbers}
    non_participants = [climber for climber in all_climbers if climber.id not in climber_ids]

    return render_template('ascents/edit_ascent.html', climbers=climbers, non_participants=non_participants, ascent_id=ascent_id, mountain=mountain)

@bp_ascents.route('/edit/add/<int:ascent_id>/<int:climber_id>', methods=['GET'])
@login_required
def edit_ascent_add(ascent_id, climber_id):
    query = '''
        INSERT INTO Ascent_Climbers (ascent_id, climber_id)
                VALUES (%s, %s)
    '''
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(query, (ascent_id, climber_id))
    db.connection().commit()
    flash(f'Пользователь успешно добавлен.', 'success')
    cursor.close()
    return redirect(url_for('ascents.edit_ascent', ascent_id=ascent_id))

@bp_ascents.route('/edit/del/<int:ascent_id>/<int:climber_id>', methods=['GET'])
@login_required
def edit_ascent_del(ascent_id, climber_id):
    query = '''
        DELETE FROM Ascent_Climbers WHERE ascent_id = %s AND climber_id = %s
    '''
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(query, (ascent_id, climber_id))
    db.connection().commit()
    flash(f'Пользователь успешно удален.', 'success')
    cursor.close()
    return redirect(url_for('ascents.edit_ascent', ascent_id=ascent_id))

@bp_ascents.route('/show/delete/<int:ascent_id>')
@login_required
def delete_ascent(ascent_id):
    query = '''
        SELECT COUNT(climber_id) as c FROM Ascent_Climbers WHERE ascent_id = %s
    '''
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(query, (ascent_id,))
    is_clear = cursor.fetchone()
    cursor.close()

    if not is_clear.c:
        query = '''
            DELETE FROM Ascents WHERE id = %s
        '''
        cursor = db.connection().cursor(named_tuple=True)
        cursor.execute(query, (ascent_id,))
        db.connection().commit()
        flash(f'Группа успешно удалена.', 'success')
        cursor.close()
        return redirect(url_for('ascents.show_ascents'))
    flash(f'Вы не можете удалить группу {ascent_id}, т.к. она не пустая!','danger')
    return redirect(url_for('ascents.show_ascents'))

@bp_ascents.route('/create', methods=['GET', 'POST'])
@login_required
def add_ascent():
    if request.method == 'POST':
        group_name = request.form['group_name']
        mountain_id = request.form['mountain_id']
        start_date = request.form['start_date']

        # Выполнение SQL-запроса для добавления новой группы восхождения
        query = '''
            INSERT INTO Ascents (mountain_id, start_date, group_name)
            VALUES (%s, %s, %s)
        '''
        cursor = db.connection().cursor(named_tuple=True)
        try:
            cursor.execute(query, (mountain_id, start_date, group_name))
            db.connection().commit()  # Сохраняем изменения
            flash('Группа восхождения успешно добавлена!', 'success')
            cursor.close()
            return redirect(url_for('ascents.show_ascents'))  # Перенаправляем на страницу со списком групп восхождения
        except Exception as e:
            db.connection().rollback()  # Откат изменений в случае ошибки
            flash('Ошибка при добавлении группы восхождения: ' + str(e), 'danger')
            cursor.close()
            return redirect(url_for('ascents.show_ascents'))

    # Получаем список вершин для отображения в выпадающем списке
    mountains_query = "SELECT id, name FROM Mountains"
    cursor = db.connection().cursor()
    cursor.execute(mountains_query)
    mountains = cursor.fetchall()
    cursor.close()

    return render_template('ascents/create.html', mountains=mountains)


