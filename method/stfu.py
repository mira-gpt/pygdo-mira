from urllib.parse import quote

from gdo.base.Application import Application
from gdo.base.Method import Method
from gdo.base.Util import Files


class stfu(Method):
    """Forget the buffered Mira context for this private or channel conversation."""

    def gdo_method_hidden(self) -> bool:
        return True

    @classmethod
    def gdo_trigger(cls) -> str:
        return 'stfu'

    def has_permission(self, user, display_error: bool = True) -> bool:
        # Check this before the base class's per-user permission cache: a user
        # allowed in private must not inherit that allowance in a channel.
        if self._env_channel and not user.is_staff():
            return False if not display_error else self.err_generic_permission()
        return super().has_permission(user, display_error)

    def context_path(self) -> str:
        channel = self._env_channel
        path = Application.temp_path(f'dog_mira/{self._env_server.get_name()}/')
        if channel:
            return path + f'channel/{quote(channel.get_name(), safe="")}.ibdes'
        return path + f'private/{quote(self._env_user.get_name(), safe="")}.ibdes'

    def gdo_execute(self):
        Files.remove(self.context_path())
        # Stay silent: a reply would be captured as a new outgoing context line.
        return self.empty()
