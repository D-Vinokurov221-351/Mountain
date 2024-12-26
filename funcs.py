import mysql.connector
from mysql.connector import Error

def create_connection():
    """ Создает подключение к базе данных MySQL """
    connection = None
    try:
        connection = mysql.connector.connect(
            host='std-mysql.ist.mospolytech.ru',
            user='std_2456_climbing_club',
            password='12345678',
            database='std_2456_climbing_club'
        )
        if connection.is_connected():
            print("Успешно подключено к базе данных")
    except Error as e:
        print(f"Ошибка '{e}' произошла при подключении к базе данных")
    return connection

def close_connection(connection):
    """ Закрывает подключение к базе данных """
    if connection.is_connected():
        connection.close()
        print("Подключение к базе данных закрыто")

def get_climbing_groups_by_mountain(connection, mountain_id):
    """Получить список групп, осуществлявших восхождение на указанную гору в хронологическом порядке."""
    query = '''
        SELECT group_name, start_date, end_date
        FROM Ascents
        WHERE mountain_id = %s
        ORDER BY start_date
    '''
    try:
        cursor = connection.cursor(named_tuple=True)
        cursor.execute(query, (mountain_id,))
        groups = cursor.fetchall()
        return groups
    except Error as e:
        print(f"Ошибка при выполнении запроса: '{e}'")
        return None
    finally:
        cursor.close()

def get_climbers_by_date_range(connection, start_date, end_date):
    """Получить список альпинистов, осуществлявших восхождение в указанный интервал дат."""
    query = '''
        SELECT DISTINCT Climbers.name
        FROM Climbers
        JOIN Ascent_Climbers ON Climbers.id = Ascent_Climbers.climber_id
        JOIN Ascents ON Ascent_Climbers.ascent_id = Ascents.id
        WHERE Ascents.start_date BETWEEN %s AND %s
    '''
    
    cursor = connection.cursor(named_tuple=True)
    cursor.execute(query, (start_date, end_date))
    climbers = cursor.fetchall()
    cursor.close()
    return climbers

def get_climber_counts_per_mountain(connection):
    """Получить информацию о количестве восхождений каждого альпиниста на каждую гору."""
    query = '''
        SELECT Climbers.name, Mountains.name AS mountain_name, COUNT(Ascent_Climbers.id) AS ascent_count
        FROM Climbers
        JOIN Ascent_Climbers ON Climbers.id = Ascent_Climbers.climber_id
        JOIN Ascents ON Ascent_Climbers.ascent_id = Ascents.id
        JOIN Mountains ON Ascents.mountain_id = Mountains.id
        GROUP BY Climbers.id, Mountains.id
        Order by mountain_name
    '''
    cursor = connection.cursor(named_tuple=True)
    cursor.execute(query)
    counts = cursor.fetchall()
    cursor.close()
    return counts

def get_climbing_groups_by_period(connection, start_date, end_date):
    """Получить список восхождений (групп), которые осуществлялись в указанный пользователем период времени."""
    query = '''
        SELECT group_name, start_date, end_date
        FROM Ascents
        WHERE start_date BETWEEN %s AND %s
    '''
    cursor = connection.cursor(named_tuple=True)
    cursor.execute(query, (start_date, end_date))
    groups = cursor.fetchall()
    cursor.close()
    return groups
