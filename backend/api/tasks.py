from celery import shared_task
import logging
from .views import fetch_and_store_all

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def fetch_and_store_all_periodic(self):
    try:
        logger.info("Starting periodic data sync task...")
        result = fetch_and_store_all(None)
        logger.info(f"Sync completed: {result.content}")
        return result.content
    except Exception as e:
        logger.error(f"Sync failed: {str(e)}")
        raise self.retry(exc=e)