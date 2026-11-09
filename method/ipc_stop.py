"""Stop the presentation in Dog without disabling the duck or mic overlay."""
from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method


class ipc_stop(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    async def gdo_execute(self):
        if not Application.IS_DOG:
            return self.empty()
        from gdo.audio.PlaybackTasks import PlaybackTasks
        await PlaybackTasks.stop()
        try:
            from gdo.audio.module_audio import module_audio
            await module_audio.instance().save_config_val('audio_microphone', '0')
        except (ImportError, RuntimeError, OSError, AttributeError) as error:
            Logger.warning(f'Agent Ears stop failed: {error}')
        try:
            from gdo.mira.ReadAlong import stop
            await stop()
        except (ImportError, RuntimeError, OSError, AttributeError) as error:
            Logger.warning(f'Readalong stop failed: {error}')
        try:
            from gdo.mira.module_mira import module_mira
            mira = module_mira.instance()
            task = getattr(mira, '_away_task', None)
            if task:
                task.cancel()
                mira._away_task = None
            from gdo.video.module_video import module_video
            module_video.instance().connector.close_effects('presentation')
        except (ImportError, RuntimeError, OSError, AttributeError) as error:
            Logger.warning(f'Presentation stop failed: {error}')
        return self.empty()
