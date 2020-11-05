from django.apps import AppConfig


class TipsConfig(AppConfig):
    name = 'tips'

    def ready(self):
        import tips.signals