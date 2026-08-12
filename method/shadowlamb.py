"""Visible Shadowlamb commands and a narrowly scoped Lamb3 reply reader."""

from pathlib import Path
from urllib.parse import quote

from gdo.base.Application import Application
from gdo.base.GDT import GDT
from gdo.base.Method import Method
from gdo.core.GDO_Server import GDO_Server
from gdo.core.GDO_User import GDO_User
from gdo.core.GDT_Name import GDT_Name
from gdo.core.GDT_RestOfText import GDT_RestOfText
from gdo.mira.util import send_to_mira


class shadowlamb(Method):
    """Send a raw command to Lamb3 and keep its enabled private reply stream visible."""

    OFFSETS: dict[str, int] = {}

    @classmethod
    def gdo_default_enabled_server(cls) -> bool:
        """Never monitor a server until its administrator explicitly opts in."""
        return False

    def gdo_user_permission(self) -> str | None:
        return 'admin'

    def gdo_in_channels(self) -> bool:
        """Mira's authenticated TCP identity may carry a virtual channel context."""
        return True

    def _disabled_in_server(self, server: GDO_Server) -> bool:
        """The local TCP control channel selects an explicitly configured target server."""
        return False if server.get_name() == 'netcat' else super()._disabled_in_server(server)

    def gdo_parameters(self) -> list[GDT]:
        return [GDT_RestOfText('command').not_null()]

    @classmethod
    def gdo_method_config_server(cls) -> list[GDT]:
        return [
            GDT_Name('nickname').not_null().initial('Lamb3'),
        ]

    @classmethod
    def gdo_method_config_user(cls) -> list[GDT]:
        return [
            GDT_Name('server').not_null().initial('wechall'),
        ]

    def cfg_server(self) -> str:
        return self.get_config_user_value('server')

    def cfg_nickname(self) -> str:
        return self.get_config_server_value('nickname')

    def target(self, server: GDO_Server) -> GDO_User | None:
        return server.get_user_by_name(self.env_server(server).cfg_nickname())

    @staticmethod
    def ibdes_path(target: GDO_User) -> Path:
        base = Application.temp_path(f'dog_mira/{target.get_server().get_name()}/private/')
        return Path(base + quote(target.get_name(), safe='') + '.ibdes')

    @staticmethod
    def reply_lines(payload: str, nickname: str) -> str:
        marker = f' {nickname}{{'
        return ''.join(line for line in payload.splitlines(keepends=True) if marker in line)

    @staticmethod
    def file_size(path: Path) -> int:
        try:
            return path.stat().st_size
        except FileNotFoundError:
            return 0

    @classmethod
    def read_new_replies(cls, path: Path, offset: int, nickname: str) -> tuple[int, str]:
        """Read only bytes appended after *offset*, safely handling a rotated file."""
        size = cls.file_size(path)
        if size < offset:
            offset = 0
        if size <= offset:
            return offset, ''
        try:
            with path.open('rb') as file:
                file.seek(offset)
                payload = file.read().decode('utf-8', errors='replace')
        except FileNotFoundError:
            return 0, ''
        return size, cls.reply_lines(payload, nickname)

    @classmethod
    async def poll_servers(cls):
        """Check one configured Lamb3 private log per explicitly enabled server."""
        for server in GDO_Server.table().all('serv_enabled'):
            method = cls().env_server(server)
            if method.get_config_server_value('disabled'):
                continue
            if not (target := method.target(server)):
                continue
            path = cls.ibdes_path(target)
            key = str(path)
            offset = cls.OFFSETS.get(key)
            if offset is None:
                cls.OFFSETS[key] = cls.file_size(path)
                continue
            offset, replies = cls.read_new_replies(path, offset, method.cfg_nickname())
            cls.OFFSETS[key] = offset
            if replies:
                send_to_mira(f'$chat\n{replies}')

    async def gdo_execute(self) -> GDT:
        if not (server := GDO_Server.table().get_by_vals({'serv_name': self.cfg_server()})):
            return self.err(f'Shadowlamb server not found: {self.cfg_server()}')
        method = self.__class__().env_server(server)
        if method.get_config_server_value('disabled'):
            return self.err(f'Shadowlamb is disabled on {server.get_name()}.')
        if not (target := method.target(server)):
            return self.err(f'Shadowlamb target not found: {method.cfg_nickname()}@{server.get_name()}')
        await server.send_to_user(target, self.param_value('command'))
        return self.empty()
