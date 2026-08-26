from gdo.base.GDT import GDT
from gdo.base.Method import Method
from gdo.core.GDT_RestOfText import GDT_RestOfText
from gdo.date.Time import Time
from gdo.mira.util import send_to_mira


class prompt(Method):
    """Deliver an explicitly addressed prompt to Mira's tmux event input."""

    @classmethod
    def gdo_trigger(cls) -> str:
        return 'mira.prompt'

    def has_permission(self, user, display_error: bool = True) -> bool:
        if self._env_channel and not user.is_staff():
            return False if not display_error else self.err_generic_permission()
        return super().has_permission(user, display_error)

    def _disabled_in_channel(self, channel) -> bool:
        from gdo.mira.method.enabled import enabled
        setting = enabled().env_channel(channel)._get_config_channel('disabled', channel)
        return setting.get_value()

    def gdo_parameters(self) -> list[GDT]:
        return [
            GDT_RestOfText('prompt').not_null(),
        ]

    def gdo_execute(self) -> GDT:
        channel = self._env_channel
        location = channel.get_name() if channel else '#-'
        text = self.param_value('prompt')
        event = f"$chat\n{Time.get_date()} {location} {self._env_user.render_name()} {text}"
        send_to_mira(event)
        return self.empty()
