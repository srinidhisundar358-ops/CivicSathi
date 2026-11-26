import logging

logger = logging.getLogger(__name__)


def send_push(notification: dict) -> bool:
    logger.info("Simulated push for notification %s", notification.get("notification_id"))
    return True
