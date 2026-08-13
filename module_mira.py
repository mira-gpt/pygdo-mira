from __future__ import annotations

import re
from urllib.parse import quote

from gdo.base.Message import Message
from gdo.base.Application import Application
from gdo.base.GDO_Module import GDO_Module
from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.base.Logger import Logger
from gdo.base.Util import Files, Strings
from gdo.core.GDO_User import GDO_User
from gdo.core.connector.Bash import Bash
from gdo.date.GDT_Duration import GDT_Duration
from gdo.date.Time import Time
from gdo.mira.util import send_to_mira
from gdo.ui.GDT_Link import GDT_Link

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gdo.ui.GDT_Page import GDT_Page


MIRA_ADDRESS = re.compile(r'^mira(?:[ :,\.!?]|$)', re.IGNORECASE)
CHAT_CONTEXT_MAX_BYTES = 7_770
SHADOWLAMB_POLL_DELAY = 0.25
HEALTH_DELAY = 30


class module_mira(GDO_Module):

    HEALTH_STATES: dict[str, bool] = {}

    ##########
    # Module #
    ##########

    def gdo_classes(self) -> list[type[GDO]]:
        return []

    def gdo_dependencies(self) -> list:
        return [
            'chat',
        ]

    async def gdo_install(self):
        pass

    def gdo_module_config(self) -> list[GDT]:
        return [
            GDT_Duration('heartbeat_delay').not_null().units(4, True).initial_value(1337.420320),
            GDT_Duration('context_max_age').not_null().min(Time.ONE_MINUTE).max(Time.ONE_DAY).initial('15m'),
        ]

    def cfg_heartbeat_delay(self) -> float:
        return self.get_config_value('heartbeat_delay')

    def cfg_context_max_age(self) -> float:
        return self.get_config_value('context_max_age')

    def gdo_user_config(self) -> list[GDT]:
        return []

    def gdo_user_settings(self) -> list[GDT]:
        return []

    def gdo_init(self):
        type(self).HEALTH_STATES = {}

    def gdo_load_scripts(self, page: 'GDT_Page'):
        self.add_js('js/pygdo-mira.js')
        self.add_css('css/pygdo-mira.css')

    def gdo_init_sidebar(self, page: 'GDT_Page'):
        page._left_bar.add_field(GDT_Link().href(self.href('overview')).text('module_mira'))

    ##########
    # Events #
    ##########

    async def get_mira(self) -> GDO_User|None:
        """
        Here you are honey. welcome to the crew ;)
        """
        return await Bash.get_server().get_or_create_user('mira')

    def gdo_subscribe_events(self):
        Application.EVENTS.add_timer_async(self.cfg_heartbeat_delay(), self.mira_is_alive, 69_696_969)
        Application.EVENTS.add_timer_async(HEALTH_DELAY, self.health_timer, Application.EVENTS.FOREVER)
        Application.EVENTS.add_timer_async(SHADOWLAMB_POLL_DELAY, self.shadowlamb_timer, Application.EVENTS.FOREVER)
        Application.EVENTS.subscribe_times('new_message', self.on_new_message, 2_238_239_328)
        Application.EVENTS.subscribe_times('msg_sent', self.on_sent_message, 2_238_239_328)
        self.subscribe('clear_cache', self.on_cc)

    async def on_cc(self):
        pass  # Conversations shall survive a cache clear and Dog restart.

    async def mira_is_alive(self):
        mira = await self.get_mira()
        await mira.send('huhu_mira')

    async def shadowlamb_timer(self):
        from gdo.mira.method.shadowlamb import shadowlamb
        await shadowlamb.poll_servers()

    def health_changes(self, states: dict[str, bool]) -> list[tuple[str, bool]]:
        """Remember connector states and return only real transitions."""
        previous = type(self).HEALTH_STATES
        changes = [(name, connected) for name, connected in states.items()
                   if name in previous and previous[name] != connected]
        type(self).HEALTH_STATES = states
        return changes

    async def health_timer(self):
        """Report enabled connector transitions locally, never into public chat."""
        from gdo.core.method.launch import launch
        states = {
            server.get_name(): server.get_connector().is_connected()
            for server in launch.SERVERS
        }
        for name, connected in self.health_changes(states):
            state = 'up' if connected else 'down'
            Logger.warning(f'Mira health: {name} is {state}.')
            send_to_mira(f'$health {name} {state}')

    async def on_new_message(self, message: Message):
        await self.on_message(message, False)

    async def on_sent_message(self, message: Message):
        await self.on_message(message, True)

    def is_channel_enabled(self, channel) -> bool:
        from gdo.mira.method.overview import overview
        setting = overview().env_channel(channel)._get_config_channel('disabled', channel)
        return not setting.get_value()

    def recent_context(self, payload: str) -> str:
        cut = Application.TIME - self.cfg_context_max_age()
        lines = []
        for line in payload.splitlines(keepends=True):
            try:
                timestamp = Time.parse_time_db(line[:26])
            except (TypeError, ValueError):
                continue
            if timestamp >= cut:
                lines.append(line)
        return ''.join(lines)

    def read_context(self, path: str) -> str:
        """Read a complete small chat file or the newest complete lines of a large one."""
        if Files.size(path) <= CHAT_CONTEXT_MAX_BYTES:
            return self.recent_context(Files.get_contents(path))

        with open(path, 'rb') as file:
            file.seek(-CHAT_CONTEXT_MAX_BYTES, 2)
            payload = file.read().decode('utf-8', errors='replace')
        # The first bytes may be a partial IBDES line; never show a broken line.
        return self.recent_context(payload.partition('\n')[2])

    @staticmethod
    def compact_chat_newlines(payload: str) -> str:
        """Keep accidental blank chat lines from splitting one IBDES record."""
        return re.sub(r'(?:\r\n|\r|\n){2,}', '\n', payload)

    async def on_message(self, message: Message, out_instead_of_in: bool=False):
        channel = message._env_channel if message._env_channel else None
        if channel and not self.is_channel_enabled(channel):
            return
        context_user = getattr(message, '_env_target_user', message._env_user) if out_instead_of_in else message._env_user
        author = message._env_user or context_user
        if author is None:
            Logger.warning('Ignoring Mira message without source or target user.')
            return
        ibdes = Time.get_date()

        if channel:
            ibdes += " " + channel.get_name()
            if channel.get_server() != message._env_server:
                ibdes += f" {channel.get_server().get_name()}"
        else:
            ibdes += ' #-'

        ibdes += f" {author.get_name()}{{{author.get_server().get_name()}}}"
        payload = (message._gdt_result.render_markdown() if message._gdt_result else message._result) if out_instead_of_in else message._message
        payload = self.compact_chat_newlines(payload)
        ibdes += f" {payload}\n"

        path = Application.temp_path(f'dog_mira/{message._env_server.get_name()}/')
        path += f"channel/{quote(channel.get_name(), safe='')}.ibdes" if channel else f"private/{quote(context_user.get_name(), safe='')}.ibdes"

        Files.create_dir(Strings.rsubstr_to(path, '/'), 0o0770)
        Files.append_content(path, ibdes)

        if MIRA_ADDRESS.match(payload) and out_instead_of_in == False:
            payload = self.read_context(path)
            if not payload:
                Files.remove(path)
                return
            try:
                send_to_mira(f"$chat\n{payload}")
            except Exception as error:
                Logger.exception(error)
            else:
                Files.remove(path)
