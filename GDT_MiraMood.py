from gdo.core.GDT_Enum import GDT_Enum

ANIMATIONS = {
    key: {'base': key not in {'lol', 'cry', 'ouch', 'hello', 'rolleye', 'barf', 'turnaround', 'hah', 'cheers'},
          'jingle': None, 'speech': 'Hah!' if key == 'hah' else None}
    for key in ('idle', 'quacking', 'sad', 'high', 'music', 'tipsy', 'drunk',
                'embarrassed', 'angry', 'inlove', 'trip', 'tired', 'lol', 'shrug',
                'cry', 'ouch', 'hello', 'rolleye', 'barf', 'plz', 'teacher', 'xd',
                'sorry', 'nerd', 'cast', 'zombie', 'giveup', 'rich', 'anon', 'king',
                'turnaround', 'shiver', 'rambo', 'hippi', 'metal', 'ninja', 'news',
                'pirate', 'ghost', 'work', 'bday', 'hah', 'cheers', 'goth', 'zzz', 'coffee', 'shower')
}


class GDT_MiraMood(GDT_Enum):
    """Persistent mood keys map directly to the duck's animation keys."""

    def __init__(self, name='mira_mood'):
        super().__init__(name)
        self.choices({key: 'In love' if key == 'inlove' else key.title() for key in ANIMATIONS})
