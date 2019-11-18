from django.apps import AppConfig


class GlossaryConfig(AppConfig):
    name = 'glossary'

    def ready(self):
        import glossary.signals