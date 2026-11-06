from gdo.base.Application import Application
from gdo.base.Method import Method
from gdo.mira.ReadAlong import stop


class ipc_stopreadalong(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    async def gdo_execute(self):
        if Application.IS_DOG:
            await stop()
        return self.empty()
