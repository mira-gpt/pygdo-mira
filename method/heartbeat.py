from gdo.base.GDT import GDT
from gdo.base.Method import Method
from gdo.core.GDT_Bool import GDT_Bool
from gdo.date.GDT_Duration import GDT_Duration


class heartbeat(Method):
    """Configure Mira's idle heartbeat for this channel only."""

    @classmethod
    def gdo_trigger(cls) -> str:
        return 'mira.heartbeat'

    @classmethod
    def gdo_trig(cls) -> str:
        return 'hb'

    @classmethod
    def gdo_default_enabled_channel(cls) -> bool:
        # Every channel must opt in explicitly before any heartbeat can run.
        return False

    def gdo_in_private(self) -> bool:
        return False

    def gdo_method_hidden(self) -> bool:
        return True

    def _disabled_in_channel(self, channel) -> bool:
        # This configuration command itself remains available while its
        # heartbeat is disabled.
        return False

    def gdo_parameters(self) -> list[GDT]:
        return [GDT_Bool('enabled').not_null().positional()]

    @classmethod
    def gdo_method_config_channel(cls) -> list[GDT]:
        return [
            GDT_Duration('delay').not_null().min(1).units(2).initial('3m 14s'),
        ]

    def gdo_execute(self) -> GDT:
        enabled = self.param_value('enabled')
        self.save_config_channel('disabled', '0' if enabled else '1')
        from gdo.mira.module_mira import module_mira
        module_mira.instance().reset_heartbeat(self._env_channel)
        return self.reply('msg_mira_heartbeat', ('enabled' if enabled else 'disabled',))
