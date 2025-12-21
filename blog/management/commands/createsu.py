import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Creates a superuser.'

    def handle(self, *args, **options):
        if not User.objects.filter(username=os.getenv('USERNAME')).exists():
            User.objects.create_superuser(
                username=os.getenv('USERNAME'),
                password=os.getenv('PASSWORD'),
                email=os.getenv('EMAIL'),
            )
        print('Superuser has been created.')