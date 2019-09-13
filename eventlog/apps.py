from django.apps import AppConfig


class EventlogConfig(AppConfig):
    name = 'eventlog'

    def ready(self):
        import eventlog.signals

