import logging

from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed

from registration.signals import user_registered, user_activated

logger = logging.getLogger('accounts')

@receiver(user_registered)
def log_user_registered(sender, user, request, **kwargs):
    logger.info('New user registered: "%(user)s"', { 'user': user })

@receiver(user_activated)
def log_user_activated(sender, user, request, **kwargs):
    logger.info('User "%(user)s" activated his account', { 'user': user })

@receiver(user_logged_in)
def log_user_logged_in(sender, request, user, **kwargs):
    logger.info('User "%(user)s" logged in', { 'user': user })

@receiver(user_logged_out)
def log_user_logged_out(sender, request, user, **kwargs):
    logger.info('User "%(user)s" logged out', { 'user': user })

@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, **kwargs):
    logger.warning('Failed login attempt with username "%s"', credentials.get('username'))
