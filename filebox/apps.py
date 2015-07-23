from django.apps import AppConfig

class FileboxAppConfig(AppConfig):
    name = 'filebox'
    verbose_name = 'FileBox'

    def ready(self):
        import filebox.accounts_logging
