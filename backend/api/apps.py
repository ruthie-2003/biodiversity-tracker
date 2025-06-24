from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class ApiConfig(AppConfig):
    name = 'api'

    def ready(self):
        # Avoids repeated execution by checking if migrations are ready
        try:
            from django.db import connection
            if connection.introspection.table_names():  # Prevents issues during initial migrations
                from django_celery_beat.models import PeriodicTask, IntervalSchedule

                schedule, _ = IntervalSchedule.objects.get_or_create(
                    every=2,
                    period=IntervalSchedule.MINUTES
                )

                task, created = PeriodicTask.objects.get_or_create(
                    interval=schedule,
                    name='Daily Taxa Sync',
                    task='api.tasks.fetch_and_store_all_periodic',
                    defaults={'enabled': True}
                )

                if created:
                    logger.info("Created new periodic task: Daily Taxa Sync")
                else:
                    if not task.enabled:
                        task.enabled = True
                        task.save()
                        logger.info("Re-enabled existing periodic task: Daily Taxa Sync")
                    else:
                        logger.info("Periodic task already exists and is enabled")

        except Exception as e:
            logger.error(f"Celery beat setup failed: {str(e)}")