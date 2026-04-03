import logging

from twilio.rest import Client
from django.conf import settings


logger = logging.getLogger(__name__)


def send_sms(to_number, message):
    if not (
        getattr(settings, "TWILIO_ACCOUNT_SID", None)
        and getattr(settings, "TWILIO_AUTH_TOKEN", None)
        and getattr(settings, "TWILIO_PHONE_NUMBER", None)
    ):
        logger.warning("sms.skipped reason=twilio_config_missing to=%s", to_number)
        return None

    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    try:
        sms_message = client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=to_number
        )
        logger.info("sms.sent to=%s sid=%s", to_number, sms_message.sid)
        return sms_message.sid
    except Exception:
        logger.exception("sms.failed to=%s", to_number)
        return None
