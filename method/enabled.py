from gdo.base.GDT import GDT
from gdo.base.Method import Method
from gdo.core.GDT_Bool import GDT_Bool


class enabled(Method):
    """Enable or disable Mira forwarding for the current channel."""

    @classmethod
    def gdo_trigger(cls) -> str:
        return 'mira'

    @classmethod
    def gdo_default_enabled_channel(cls) -> bool:
        return False

    def gdo_in_private(self) -> bool:
        return False

    def _disabled_in_channel(self, channel) -> bool:
        """The toggle itself must stay available while forwarding is disabled."""
        return False

    def gdo_parameters(self) -> list[GDT]:
        return [
            GDT_Bool('enabled').not_null().positional(),
        ]

    def gdo_execute(self) -> GDT:
        enabled = self.param_value('enabled')
        self.save_config_channel('disabled', '0' if enabled else '1')
        return self.msg('msg_mira_enabled', ('enabled' if enabled else 'disabled',))
