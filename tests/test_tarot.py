from tarot import DECK, draw_cards


def test_tarot_deck_has_78_unique_cards():
    assert len(DECK) == 78
    assert len(set(DECK)) == 78


def test_draw_cards_are_unique():
    cards = draw_cards(5)
    assert len(cards) == 5
    assert len({card.name for card in cards}) == 5
    assert all(card.orientation in {"прямая", "перевёрнутая"} for card in cards)
