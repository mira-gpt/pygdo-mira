from gdo.core.GDT_Enum import GDT_Enum


class GDT_MiraMood(GDT_Enum):
    """Persistent mood keys map directly to the duck's animation keys."""

    def __init__(self, name='mira_mood'):
        super().__init__(name)
        self.choices({'idle': 'Idle', 'quacking': 'Quacking', 'sad': 'Sad', 'high': 'High', 'music': 'Music', 'tipsy': 'Tipsy', 'drunk': 'Drunk', 'embarrassed': 'Embarrassed', 'angry': 'Angry', 'inlove': 'In love', 'trip': 'Trip', 'tired': 'Tired'})
        self._choices.update({key: key.title() for key in ('lol', 'shrug', 'cry', 'ouch', 'hello', 'rolleye', 'barf', 'plz', 'teacher', 'xd', 'sorry', 'nerd', 'cast', 'zombie', 'giveup', 'rich', 'anon', 'king', 'turnaround', 'shiver', 'rambo', 'hippi', 'metal', 'ninja', 'news', 'pirate')})
