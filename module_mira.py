from __future__ import annotations

import re
from urllib.parse import quote

from gdo.base.Message import Message
from gdo.base.Application import Application
from gdo.base.GDO_Module import GDO_Module
from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.base.Logger import Logger
from gdo.base.Render import Mode
from gdo.base.Util import Files, Strings
from gdo.core.GDO_User import GDO_User
from gdo.core.GDT_Bool import GDT_Bool
from gdo.core.GDT_String import GDT_String
from gdo.core.connector.Bash import Bash
from gdo.date.GDT_Duration import GDT_Duration
from gdo.date.Time import Time
from gdo.mira.util import send_to_mira

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gdo.ui.GDT_Page import GDT_Page


# Default address for backwards compatibility. Runtime matching uses the
# configurable agent name below, so a second installation can answer to e.g.
# ``simion`` without also reacting to ``mira``.
MIRA_ADDRESS = re.compile(r'(?<![a-z])mira(?![a-z])', re.IGNORECASE)
CHAT_CONTEXT_MAX_BYTES = 7_770
SHADOWLAMB_POLL_DELAY = 0.25
HEALTH_DELAY = 30
HEARTBEAT_CHECK_DELAY = 1
# A WebSocket/Web mirror of an IRC line can arrive a few milliseconds after
# the original line.  Keep it out of Mira's conversational context without
# suppressing a deliberate repeated line on the same connector.
INBOUND_MIRROR_WINDOW = 1.0


class module_mira(GDO_Module):

    HEALTH_STATES: dict[str, bool] = {}
    HEARTBEAT_ACTIVITY: dict[str, tuple] = {}
    HEARTBEAT_SENT: set[str] = set()
    INBOUND_CONTEXT: dict[tuple[str, str, str], tuple[str, float]] = {}

    ##########
    # Module #
    ##########

    def gdo_classes(self) -> list[type[GDO]]:
        return []

    def gdo_dependencies(self) -> list:
        return [
            'chat',
        ]

    def gdo_main_method_name(self) -> str:
        return 'hey_there'

    async def gdo_install(self):
        pass

    def gdo_module_config(self) -> list[GDT]:
        return [
            GDT_String('agent_name').ascii().minlen(1).maxlen(32).not_null().initial('mira'),
            GDT_Duration('heartbeat_delay').not_null().units(4, True).initial_value(1337.420320),
            GDT_Duration('context_max_age').not_null().min(Time.ONE_MINUTE).max(Time.ONE_DAY).initial('15m'),
        ]

    def cfg_agent_name(self) -> str:
        return self.get_config_value('agent_name')

    @staticmethod
    def address_pattern(agent_name: str) -> re.Pattern:
        """Match an agent name as a standalone word in natural chat text."""
        return re.compile(rf'(?<![a-z]){re.escape(agent_name)}(?![a-z])', re.IGNORECASE)

    def is_addressed(self, payload: str) -> bool:
        return bool(self.address_pattern(self.cfg_agent_name()).search(payload))

    def cfg_heartbeat_delay(self) -> float:
        return self.get_config_value('heartbeat_delay')

    def cfg_context_max_age(self) -> float:
        return self.get_config_value('context_max_age')

    def gdo_user_config(self) -> list[GDT]:
        # Permission for private conversations forwarded to Mira. Public
        # channel interaction stays open for normal community use.
        return [
            GDT_Bool('mira_enabled').not_null().initial('1').hidden(),
        ]

    def gdo_user_settings(self) -> list[GDT]:
        return []

    def gdo_init(self):
        type(self).HEALTH_STATES = {}
        type(self).HEARTBEAT_ACTIVITY = {}
        type(self).HEARTBEAT_SENT = set()
        type(self).INBOUND_CONTEXT = {}

    def gdo_load_scripts(self, page: 'GDT_Page'):
        self.add_js('js/pygdo-mira.js')
        self.add_css('css/pygdo-mira.css')

    ##########
    # Events #
    ##########

    async def get_mira(self) -> GDO_User|None:
        """
        Here you are honey. welcome to the crew ;)
        """
        return await Bash.get_server().get_or_create_user('mira')

    def gdo_subscribe_events(self):
        # Application.EVENTS.add_timer_async(self.cfg_heartbeat_delay(), self.mira_is_alive, 69_696_969)
        Application.EVENTS.add_timer_async(HEALTH_DELAY, self.health_timer, Application.EVENTS.FOREVER)
        Application.EVENTS.add_timer_async(HEARTBEAT_CHECK_DELAY, self.heartbeat_timer, Application.EVENTS.FOREVER)
        Application.EVENTS.add_timer_async(SHADOWLAMB_POLL_DELAY, self.shadowlamb_timer, Application.EVENTS.FOREVER)
        Application.EVENTS.subscribe_times('new_message', self.on_new_message, 2_238_239_328)
        Application.EVENTS.subscribe_times('msg_sent', self.on_sent_message, 2_238_239_328)
        self.subscribe('clear_cache', self.on_cc)

    async def on_cc(self):
        pass  # Conversations shall survive a cache clear and Dog restart.

    # async def mira_is_alive(self):
    #     mira = await self.get_mira()
    #     await mira.send('huhu_mira')

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
        self.reset_heartbeat(message._env_channel)
        await self.on_message(message, False)

    async def on_sent_message(self, message: Message):
        await self.on_message(message, True)

    def is_channel_enabled(self, channel) -> bool:
        from gdo.mira.method.enabled import enabled
        setting = enabled().env_channel(channel)._get_config_channel('disabled', channel)
        return not setting.get_value()

    @staticmethod
    def heartbeat_method(channel):
        from gdo.mira.method.heartbeat import heartbeat
        return heartbeat().env_channel(channel)

    def heartbeat_enabled(self, channel) -> bool:
        if channel is None:
            return False
        return (self.is_channel_enabled(channel) and
                not self.heartbeat_method(channel).get_config_channel_value('disabled'))

    def reset_heartbeat(self, channel, now: float | None = None):
        """Record channel activity and allow one later idle notification."""
        if not self.heartbeat_enabled(channel):
            return
        now = Application.TIME if now is None else now
        channel_id = channel.get_id()
        type(self).HEARTBEAT_ACTIVITY[channel_id] = (channel, now)
        type(self).HEARTBEAT_SENT.discard(channel_id)

    def heartbeat_due(self, channel, last_activity: float, now: float | None = None) -> bool:
        """A channel receives at most one heartbeat until new activity arrives."""
        now = Application.TIME if now is None else now
        delay = self.heartbeat_method(channel).get_config_channel_value('delay')
        return now - last_activity >= delay

    @staticmethod
    def channel_context_path(channel) -> str:
        path = Application.temp_path(f'dog_mira/{channel.get_server().get_name()}/channel/')
        return path + f'{quote(channel.get_name(), safe="")}.ibdes'

    def heartbeat_payload(self, channel) -> str:
        """Include the same recent IBDES history used for ordinary chat turns."""
        path = self.channel_context_path(channel)
        if not Files.exists(path):
            return ''
        return self.read_context(path)

    @classmethod
    def heartbeat_event(cls, channel, payload: str) -> str:
        """Wrap an idle notification with the channel's reply-language hint."""
        return f'$heartbeat #{channel.get_id()} --lang={cls.chat_language(channel)}\n{payload}'

    async def heartbeat_timer(self):
        for channel_id, (channel, last_activity) in list(type(self).HEARTBEAT_ACTIVITY.items()):
            if not self.heartbeat_enabled(channel):
                type(self).HEARTBEAT_ACTIVITY.pop(channel_id, None)
                type(self).HEARTBEAT_SENT.discard(channel_id)
                continue
            if channel_id not in type(self).HEARTBEAT_SENT and self.heartbeat_due(channel, last_activity):
                # This is a private local prompt for Mira, not an unsolicited
                # channel message. Mira decides whether the silence merits a reply.
                try:
                    path = self.channel_context_path(channel)
                    payload = self.heartbeat_payload(channel)
                    if not payload:
                        continue
                    send_to_mira(self.heartbeat_event(channel, payload))
                    # A heartbeat is a real context hand-off, just like an
                    # addressed $chat prompt. Consume its snapshot so the
                    # next idle wake-up only contains new conversation.
                    Files.remove(path)
                except Exception as error:
                    Logger.exception(error)
                else:
                    type(self).HEARTBEAT_SENT.add(channel_id)

    @staticmethod
    def is_user_enabled(user: GDO_User) -> bool:
        """Whether this user permits their messages to reach Mira's context."""
        return bool(user.get_setting_value('mira_enabled'))

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

    @staticmethod
    def is_toggle_command(payload: str, trigger: str) -> bool:
        """The channel toggle changes forwarding, but is never conversation."""
        return bool(re.match(rf'^{re.escape(trigger)}mira(?:\s|$)', payload, re.IGNORECASE))

    @staticmethod
    def ibdes_payload(message: Message, out_instead_of_in: bool) -> str:
        """Return the visible text for one IBDES record.

        Outbound connector messages already carry their rendered text in
        ``_result``.  A command such as ``say.in`` has an empty method result
        and therefore an empty page top bar; reading only the latter produced
        useless blank Dog records in IBDES.
        """
        if not out_instead_of_in:
            return message._message
        return message._result or Application.get_page()._top_bar.render(Mode.render_cli)

    @staticmethod
    def ibdes_channel(channel) -> str:
        """Render the canonical reply target for an IBDES record.

        A persisted channel ID is stable and can be passed directly to
        ``say.in``. Display names and connector-specific channel names are
        deliberately omitted here: they require a lookup and may be
        ambiguous across connectors.
        """
        return f'#{channel.get_id()}' if channel else '#-'

    @staticmethod
    def ibdes_author(message: Message, out_instead_of_in: bool):
        """Return the identity which IBDES must expose for this record.

        Incoming messages execute as a linked account's effective user, but a
        Mira reply must return through the connector that actually sent the
        message.  ``_env_reply_to`` preserves that connector identity.
        """
        if not out_instead_of_in:
            return getattr(message, '_env_reply_to', None) or message._env_user
        return message._env_user or getattr(message, '_env_target_user', None)

    @staticmethod
    def chat_language(channel) -> str:
        """Return a safe ISO-639-1 hint for a routed ``$chat`` event."""
        language = channel.get_lang_iso() if channel else 'en'
        language = str(language).lower()
        return language if re.fullmatch(r'[a-z]{2}', language) else 'en'

    @classmethod
    def chat_event(cls, channel, payload: str) -> str:
        """Wrap routed context with its channel's reply-language hint."""
        return f'$chat --lang={cls.chat_language(channel)}\n{payload}'

    @staticmethod
    def is_shadowlamb_reply(channel, author, server) -> bool:
        """Private Lamb3 replies belong exclusively to the Shadowlamb bridge."""
        if channel is not None:
            return False
        from gdo.mira.method.shadowlamb import shadowlamb
        method = shadowlamb().env_server(server)
        return (not method.get_config_server_value('disabled') and
                author.get_name().casefold() == method.cfg_nickname().casefold())

    @classmethod
    def is_mirrored_inbound(cls, channel, account, source, payload: str,
                            now: float | None = None) -> bool:
        """Reject one near-simultaneous cross-connector mirror.

        Browser/live-chat delivery must not turn an IRC line from a linked
        account into a second ``{Web}`` line in Mira's context.  Repeats on
        the *same* connector are intentionally retained.
        """
        now = Application.TIME if now is None else now
        context = cls.INBOUND_CONTEXT
        context = {
            key: value for key, value in context.items()
            if now - value[1] <= INBOUND_MIRROR_WINDOW
        }
        cls.INBOUND_CONTEXT = context
        key = (str(channel.get_id()) if channel else '-', str(account.get_id()), payload.strip())
        source_id = str(source.get_id())
        previous = context.get(key)
        context[key] = (source_id, now)
        return bool(previous and previous[0] != source_id and now - previous[1] <= INBOUND_MIRROR_WINDOW)

    async def on_message(self, message: Message, out_instead_of_in: bool=False):
        # LinkUUp HTTP input reaches the Dog through its explicit IPC queue. Its
        # room channels are Mira conversations by design, so do not require users
        # to type a second "mira" address or enable every virtual room manually.
        is_lup = bool(message._env_server and message._env_server.gdo_val('serv_connector') == 'lup')
        if not out_instead_of_in:
            # Events normally arrive before command parsing, while delayed
            # listeners can see the already parsed method.  Cover both so
            # `$mira 1` cannot enable its own forwarding into Mira's context.
            if self.is_toggle_command(message._message, message.get_trigger()):
                return
            if getattr(message, '_method', None) and message._method.gdo_trigger() == 'mira':
                return
        channel = message._env_channel if message._env_channel else None
        if channel and not is_lup and not self.is_channel_enabled(channel):
            return
        context_user = getattr(message, '_env_target_user', message._env_user) if out_instead_of_in else self.ibdes_author(message, False)
        author = self.ibdes_author(message, out_instead_of_in) or context_user
        if author is None:
            Logger.error('Ignoring Mira message without source or target user.')
            return
        # Public channels remain open; private chats require the user's
        # explicit per-user permission (enabled by default for now).
        if channel is None and not out_instead_of_in and not self.is_user_enabled(author):
            return
        ibdes = Time.get_date()

        ibdes += ' ' + self.ibdes_channel(channel)

        ibdes += f" {author.get_name()}{{{author.get_server().get_name()}}}"
        payload = self.ibdes_payload(message, out_instead_of_in)
        payload = self.compact_chat_newlines(payload)
        if not payload.strip():
            return
        if not out_instead_of_in and self.is_mirrored_inbound(
                channel, author.get_effective_user(), message._env_server, payload):
            Logger.debug(f'Ignoring mirrored Mira input from {message._env_server.get_name()}.')
            return
        ibdes += f" {payload}\n"

        path = Application.temp_path(f'dog_mira/{message._env_server.get_name()}/')
        path += f"channel/{quote(channel.get_name(), safe='')}.ibdes" if channel else f"private/{quote(context_user.get_name(), safe='')}.ibdes"

        Files.create_dir(Strings.rsubstr_to(path, '/'), 0o0770)
        Files.append_content(path, ibdes)

        # Lamb3 private replies are consumed by shadowlamb.poll_servers().
        # Their game text regularly contains "mira", which must not make the
        # ordinary address/heartbeat path forward the same private log too.
        if self.is_shadowlamb_reply(channel, author, message._env_server):
            return

        if (is_lup or self.is_addressed(payload)) and out_instead_of_in == False:
            payload = self.read_context(path)
            if not payload:
                Files.remove(path)
                return
            try:
                send_to_mira(self.chat_event(channel, payload))
            except Exception as error:
                Logger.exception(error)
            else:
                Files.remove(path)
