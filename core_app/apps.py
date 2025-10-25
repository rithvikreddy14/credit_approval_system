from django.apps import AppConfig
from django.db.utils import OperationalError

class CoreAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core_app'

    def ready(self):
        """
        Called when the application is initialized.
        Triggers the initial data ingestion as a background task.
        """
        try:
            from workers.ingest_data import start_ingestion_if_needed
            start_ingestion_if_needed()
        except ImportError:
            # Occurs during initial setup before files are fully moved
            pass 
        except OperationalError:
            # Handle case where DB is not ready yet
            pass