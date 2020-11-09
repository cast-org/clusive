from django.apps import AppConfig


class RosterConfig(AppConfig):
    name = 'roster'

    def ready(self):
        import roster.signals