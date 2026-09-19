from __future__ import annotations

import secrets

from creative_tools import TarotCard

MAJORS = [
    'Шут', 'Маг', 'Верховная Жрица', 'Императрица', 'Император',
    'Иерофант', 'Влюблённые', 'Колесница', 'Сила', 'Отшельник',
    'Колесо Фортуны', 'Справедливость', 'Повешенный', 'Смерть',
    'Умеренность', 'Дьявол', 'Башня', 'Звезда', 'Луна', 'Солнце',
    'Суд', 'Мир',
]

RANKS = [
    'Туз', 'Двойка', 'Тройка', 'Четвёрка', 'Пятёрка', 'Шестёрка',
    'Семёрка', 'Восьмёрка', 'Девятка', 'Десятка',
    'Паж', 'Рыцарь', 'Королева', 'Король',
]

SUITS = ['Жезлов', 'Кубков', 'Мечей', 'Пентаклей']

DECK = MAJORS + [f'{rank} {suit}' for suit in SUITS for rank in RANKS]


def draw_cards(count: int = 3) -> list[TarotCard]:
    count = min(max(count, 1), 10)
    rng = secrets.SystemRandom()
    names = rng.sample(DECK, count)
    return [
        TarotCard(name=name, orientation=rng.choice(['прямая', 'перевёрнутая']))
        for name in names
    ]
