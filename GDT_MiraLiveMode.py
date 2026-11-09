from gdo.core.GDT_Enum import GDT_Enum


class GDT_MiraLiveMode(GDT_Enum):
    MODES = ('off', 'work', 'show', 'discuss', 'cohost')

    def __init__(self, name='mira_livemode'):
        super().__init__(name)
        self.choices({mode: mode.title() for mode in self.MODES})
