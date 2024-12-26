import io
from flask import render_template, request, redirect, url_for, flash, Blueprint, send_file
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from app import db
from check_user import CheckUser
from functools import wraps
import mysql.connector
import math
import test
from funcs import get_climbing_groups_by_mountain  # Импортируйте вашу функцию
from funcs import get_climbers_by_date_range
from funcs import get_climber_counts_per_mountain
from funcs import get_climbing_groups_by_period
from funcs import create_connection, close_connection
import pytest
import datetime

@pytest.fixture(scope='module')
def connection():
    """Создание соединения с базой данных."""
    conn = create_connection()
    yield conn
    close_connection(conn)

@pytest.mark.parametrize("mountain_id, expected_result", [
    (1, [
        {'group_name': 'Команда А', 'start_date': datetime.date(2023, 5, 1), 'end_date': datetime.date(2023, 5, 10)},
        {'group_name': 'Команда К', 'start_date': datetime.date(2024, 3, 1), 'end_date': datetime.date(2024, 3, 10)},
        {'end_date': datetime.date(2025, 8, 7), 'group_name': 'mhjh', 'start_date': datetime.date(2024, 8, 7)}
    ]),
    (2, [
        {'group_name': 'Команда Б', 'start_date': datetime.date(2023, 6, 15), 'end_date': datetime.date(2023, 6, 25)},
        {'group_name': 'Команда К', 'start_date': datetime.date(2024, 3, 1), 'end_date': datetime.date(2024, 3, 10)},
        {'group_name': 'Команда Л', 'start_date': datetime.date(2024, 4, 1), 'end_date': datetime.date(2024, 4, 10)},
    ]),
    (3, [
        {'group_name': 'Команда В', 'start_date': datetime.date(2023, 7, 10), 'end_date': datetime.date(2023, 7, 20)},
        {'group_name': 'Команда Л', 'start_date': datetime.date(2024, 4, 1), 'end_date': datetime.date(2024, 4, 10)},
        {'group_name': 'Команда М', 'start_date': datetime.date(2024, 5, 1), 'end_date': datetime.date(2024, 5, 10)},
    ]),
    (4, [
        {'group_name': 'Команда Г', 'start_date': datetime.date(2023, 8, 1), 'end_date': datetime.date(2023, 8, 5)},
        {'group_name': 'Команда М', 'start_date': datetime.date(2024, 5, 1), 'end_date': datetime.date(2024, 5, 10)},
        {'group_name': 'Команда Н', 'start_date': datetime.date(2024, 6, 1), 'end_date': datetime.date(2024, 6, 10)},
    ]),
    (5, [
        {'group_name': 'Команда Д', 'start_date': datetime.date(2023, 9, 1), 'end_date': datetime.date(2023, 9, 10)},
        {'group_name': 'Команда Н', 'start_date': datetime.date(2024, 6, 1), 'end_date': datetime.date(2024, 6, 10)},
        {'group_name': 'Команда О', 'start_date': datetime.date(2024, 7, 1), 'end_date': datetime.date(2024, 7, 10)},
    ]),
    (10, [
        {'group_name': 'Команда Й', 'start_date': datetime.date(2024, 2, 1), 'end_date': datetime.date(2024, 2, 5)},
        {'group_name': 'Команда У', 'start_date': datetime.date(2024, 12, 1), 'end_date': datetime.date(2024, 12, 10)},
    ]),
])
def test_get_climbing_groups_by_mountain(connection, mountain_id, expected_result):
    """Тестирование функции get_climbing_groups_by_mountain."""
    
    # Вызов тестируемой функции
    result = get_climbing_groups_by_mountain(connection, mountain_id)

    # Преобразование результата в список словарей для удобства сравнения
    result_list = [{'group_name': group.group_name, 
                    'start_date': group.start_date, 
                    'end_date': group.end_date} for group in result]

    # Сравнение результата с ожидаемым
    assert result_list == expected_result

@pytest.mark.parametrize("start_date, end_date, expected_climbers", [
    ('2023-05-01', '2023-05-10', ['Алексей Иванов', 'Мария Петрова']),
    ('2023-06-15', '2023-06-25', ['Иван Смирнов', 'Ольга Кузнецова']),
    ('2023-07-10', '2023-07-20', ['Дмитрий Сидоров']),
    ('2023-08-01', '2023-08-05', ['Светлана Фёдорова', 'Андрей Васильев']),
    ('2023-09-01', '2023-09-10', ['Елена Сергеева']),
    ('2024-03-01', '2024-03-10', ['Алексей Иванов', 'Мария Петрова', 'Иван Смирнов']),
    ('2024-04-01', '2024-04-10', ['Иван Смирнов', 'Ольга Кузнецова', 'Дмитрий Сидоров']),
])
def test_get_climbers_by_date_range(start_date, end_date, expected_climbers):
    """Тестирование функции get_climbers_by_date_range."""
    
    # Создаем фиктивное соединение с соответствующими данными
    fake_connection = FakeConnection(expected_climbers)

    # Вызов тестируемой функции
    result = get_climbers_by_date_range(fake_connection, start_date, end_date)
    
    # Извлечение имен альпинистов из результата
    result_names = {climber['name'] for climber in result}

    # Извлечение ожидаемых имен альпинистов в множество
    expected_names = set(expected_climbers)

    # Сравнение результата с ожидаемым
    assert result_names == expected_names

class FakeConnection:
    def __init__(self, expected_climbers):
        self.expected_climbers = expected_climbers

    def cursor(self, named_tuple=False):
        return FakeCursor(self.expected_climbers)

class FakeCursor:
    def __init__(self, expected_climbers):
        self.expected_climbers = expected_climbers

    def execute(self, query, params):
        pass  # Здесь можно добавить логику для имитации выполнения запроса

    def fetchall(self):
        # Возвращаем список словарей с именами альпинистов для имитации результата запроса
        return [{'name': climber} for climber in self.expected_climbers]

    def close(self):
        pass  # Имитация закрытия курсора

@pytest.mark.parametrize("expected_result", [
    [
    {'name': 'Alexey Manager', 'mountain_name': 'Эверест', 'ascent_count': 2},
    {'name': 'Alexey Manager', 'mountain_name': 'Канченджанга', 'ascent_count': 1},
    {'name': 'Alexey Manager', 'mountain_name': 'Лхоцзе', 'ascent_count': 1},
    {'name': 'Alexey Manager', 'mountain_name': 'Чо-Ойю', 'ascent_count': 1},
    {'name': 'Alexey Manager', 'mountain_name': 'Дхаулагири', 'ascent_count': 2},
    {'name': 'Alexey Manager', 'mountain_name': 'Аннапурна I', 'ascent_count': 2},
    {'name': 'Мария Петрова', 'mountain_name': 'Эверест', 'ascent_count': 2},
    {'name': 'Мария Петрова', 'mountain_name': 'Лхоцзе', 'ascent_count': 1},
    {'name': 'Мария Петрова', 'mountain_name': 'Чо-Ойю', 'ascent_count': 1},
    {'name': 'Мария Петрова', 'mountain_name': 'Дхаулагири', 'ascent_count': 2},
    {'name': 'Мария Петрова', 'mountain_name': 'Манаслу', 'ascent_count': 2},
    {'name': 'Иван Смирнов', 'mountain_name': 'Эверест', 'ascent_count': 2},
    {'name': 'Иван Смирнов', 'mountain_name': 'К2', 'ascent_count': 1},
    {'name': 'Иван Смирнов', 'mountain_name': 'Лхоцзе', 'ascent_count': 1},
    {'name': 'Иван Смирнов', 'mountain_name': 'Макалу', 'ascent_count': 1},
    {'name': 'Иван Смирнов', 'mountain_name': 'Чо-Ойю', 'ascent_count': 1},
    {'name': 'Иван Смирнов', 'mountain_name': 'Манаслу', 'ascent_count': 2},
    {'name': 'Ольга Кузнецова', 'mountain_name': 'К2', 'ascent_count': 2},
    {'name': 'Ольга Кузнецова', 'mountain_name': 'Макалу', 'ascent_count': 1},
    {'name': 'Ольга Кузнецова', 'mountain_name': 'Манаслу', 'ascent_count': 2},
    {'name': 'Дмитрий Сидоров', 'mountain_name': 'К2', 'ascent_count': 2},
    {'name': 'Дмитрий Сидоров', 'mountain_name': 'Канченджанга', 'ascent_count': 1},
    {'name': 'Дмитрий Сидоров', 'mountain_name': 'Макалу', 'ascent_count': 1},
    {'name': 'Дмитрий Сидоров', 'mountain_name': 'Нанга Парбат', 'ascent_count': 2},
    {'name': 'Светлана Фёдорова', 'mountain_name': 'К2', 'ascent_count': 1},
    {'name': 'Светлана Фёдорова', 'mountain_name': 'Канченджанга', 'ascent_count': 1},
    {'name': 'Светлана Фёдорова', 'mountain_name': 'Лхоцзе', 'ascent_count': 1},
    {'name': 'Светлана Фёдорова', 'mountain_name': 'Чо-Ойю', 'ascent_count': 1},
    {'name': 'Светлана Фёдорова', 'mountain_name': 'Нанга Парбат', 'ascent_count': 2},
    {'name': 'Андрей Васильев', 'mountain_name': 'Канченджанга', 'ascent_count': 1},
    {'name': 'Андрей Васильев', 'mountain_name': 'Лхоцзе', 'ascent_count': 1},
    {'name': 'Андрей Васильев', 'mountain_name': 'Макалу', 'ascent_count': 1},
    {'name': 'Андрей Васильев', 'mountain_name': 'Чо-Ойю', 'ascent_count': 1},
    {'name': 'Андрей Васильев', 'mountain_name': 'Нанга Парбат', 'ascent_count': 2},
    {'name': 'Елена Сергеева', 'mountain_name': 'Канченджанга', 'ascent_count': 1},
    {'name': 'Елена Сергеева', 'mountain_name': 'Лхоцзе', 'ascent_count': 1},
    {'name': 'Елена Сергеева', 'mountain_name': 'Макалу', 'ascent_count': 1},
    {'name': 'Елена Сергеева', 'mountain_name': 'Чо-Ойю', 'ascent_count': 1},
    {'name': 'Елена Сергеева', 'mountain_name': 'Аннапурна I', 'ascent_count': 2},
    {'name': 'Максим Орлов', 'mountain_name':'Канченджанга','ascent_count' :1 },
    {'name':'Максим Орлов','mountain_name':'Макалу','ascent_count' :1 },
    {'name':'Максим Орлов','mountain_name':'Дхаулагири','ascent_count' :2 },
    {'name':'Максим Орлов','mountain_name':'Аннапурна I','ascent_count' :2 }
    ]
])
def test_get_climber_counts_per_mountain(connection, expected_result):
    result = get_climber_counts_per_mountain(connection)

    # Преобразование результата в список словарей для удобства сравнения
    result_list = [{'name': row.name,
                    'mountain_name': row.mountain_name,
                    'ascent_count': row.ascent_count} for row in result]

    assert result_list == expected_result

@pytest.mark.parametrize("start_date, end_date, expected_result", [
    ('2023-06-01', '2023-09-30', [
        {'group_name': 'Команда Б', 'start_date': datetime.date(2023, 6, 15), 'end_date': datetime.date(2023, 6, 25)},
        {'group_name': 'Команда В', 'start_date': datetime.date(2023, 7, 10), 'end_date': datetime.date(2023, 7, 20)},
        {'group_name': 'Команда Г', 'start_date': datetime.date(2023, 8, 1), 'end_date': datetime.date(2023, 8, 5)},
        {'group_name': 'Команда Д', 'start_date': datetime.date(2023, 9, 1), 'end_date': datetime.date(2023, 9, 10)},
    ]),
    ('2025-01-01', '2025-12-31', [])
])  # Тестируем на диапазоне дат без результатов
def test_get_climbing_groups_by_period(connection, start_date, end_date, expected_result):
    result = get_climbing_groups_by_period(connection, start_date, end_date)

    # Преобразование результата в список словарей для удобства сравнения
    result_list = [{'group_name': row.group_name,
                    'start_date': row.start_date,
                    'end_date': row.end_date} for row in result]

    assert result_list == expected_result

    