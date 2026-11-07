from gdo.core.GDT_Enum import GDT_Enum


class GDT_MiraMood(GDT_Enum):
    """Persistent mood keys map directly to the duck's animation keys."""

    def __init__(self, name='mira_mood'):
        super().__init__(name)
        self.choices({'idle': 'Idle', 'quacking': 'Quacking', 'sad': 'Sad', 'high': 'High', 'music': 'Music', 'tipsy': 'Tipsy', 'drunk': 'Drunk', 'embarrassed': 'Embarrassed', 'angry': 'Angry', 'inlove': 'In love'})
