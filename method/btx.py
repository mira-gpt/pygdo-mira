"""Submit a user-attributed message to the live microphone ticker."""
from gdo.base.Method import Method
from gdo.core.GDT_RestOfText import GDT_RestOfText
from gdo.mira.BtxPricing import btx_price
from gdo.mira.module_mira import module_mira
from gdo.video.method.mic_ticker import queue_ticker


class btx(Method):
    @classmethod
    def gdo_trig(cls):
        return 'btx'

    def gdo_needs_authentication(self):
        return True

    def gdo_parameters(self):
        return [GDT_RestOfText('text').minlen(1).maxlen(200).not_null()]

    def gdo_method_price(self):
        text = self.param_val('text', False)
        if not text:
            return 0
        rate = module_mira.instance().get_config_val('mira_btx_creds_per_letter') or '1.00'
        return btx_price(text, rate)

    def gdo_execute(self):
        try:
            text = self.param_val('text')
            if any(c in text for c in '\r\n\x00'):
                raise ValueError('Text must be a single line')
            if not self._env_user.is_authenticated() or not self._env_user.is_persisted():
                return self.err('mira_btx_auth')
            price = self.gdo_method_price()
            if not self.has_price_permission(self._env_user):
                return self.empty()
            name = ''.join(c for c in self._env_user.get_name() if c.isprintable())[:50]
            queue_ticker(f'{name}: {text}')
            return self.reply('mira_btx_queued', (str(price),))
        except (ValueError, RuntimeError, OSError) as error:
            return self.err('mira_btx_error', (str(error),))
