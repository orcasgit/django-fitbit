"""
This django management command can be used to refresh user access tokens.
Running without arguments will refresh only the tokens that are expired.

Using the ``--all`` option will refresh all access tokens, whether expired or
not.

Using the ``--deauth`` option tells the command to remove the ``UserFitbit``
object for any tokens that fail to refresh for whatever reason. This can be
handy to prune ``UserFitbit`` objects that have somehow managed to get an
invalid refresh token (an unrecoverable state).
"""

import time

from django.core.management.base import BaseCommand, CommandError
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError

from fitapp.models import UserFitbit
from fitapp.utils import create_fitbit


class Command(BaseCommand):
    help = """
        Refreshes user access tokens, optionally deleting UserFitbit objects
        when the refresh token is invalid
    """

    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument(
            '--all',
            action='store_true',
            dest='all',
            default=False,
            help='Refresh all tokens, not just the expired ones',
        )
        parser.add_argument(
            '--deauth',
            action='store_true',
            dest='deauth',
            default=False,
            help='Deauth (remove UserFitbit) when refresh token is invalid',
        )

    def handle(self, *args, **options):
        user_fitbits = UserFitbit.objects.all()
        if not options['all']:
            user_fitbits = user_fitbits.filter(expires_at__lt=time.time())
        success, failed = 0, 0
        for user_fitbit in user_fitbits:
            fitbit = create_fitbit(**user_fitbit.get_user_data())
            try:
                fitbit.client.refresh_token()
                success += 1
            except InvalidGrantError:
                if options['deauth']:
                    user_fitbit.delete()
                failed += 1
        msg = 'Successfully refreshed {} tokens'.format(success)
        # Django 1.8 doesn't have the SUCCESS style, fallback to WARNING
        success_style = getattr(self.style, 'SUCCESS', self.style.WARNING)
        self.stdout.write(success_style(msg))
        if failed > 0:
            msg = 'Failed to refresh {} tokens'.format(failed)
            self.stdout.write(self.style.ERROR(msg))
        if options['deauth']:
            msg = 'Deauthenticated {} users'.format(failed)
            self.stdout.write(self.style.NOTICE(msg))
