from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
from django.conf import settings


class Command(BaseCommand):
    help = 'Setup Google OAuth configuration for django-allauth'

    def add_arguments(self, parser):
        parser.add_argument(
            '--domain',
            type=str,
            default='localhost:8000',
            help='Domain for the site (default: localhost:8000)'
        )
        parser.add_argument(
            '--site-name',
            type=str,
            default='Krushi Local',
            help='Name for the site (default: Krushi Local)'
        )

    def handle(self, *args, **options):
        domain = options['domain']
        site_name = options['site_name']

        self.stdout.write(self.style.WARNING('Setting up Google OAuth...'))

        # Step 1: Configure Site
        self.stdout.write('\n1. Configuring Django Site...')
        try:
            site = Site.objects.get(id=settings.SITE_ID)
            site.domain = domain
            site.name = site_name
            site.save()
            self.stdout.write(self.style.SUCCESS(f'   ✓ Site configured: {domain}'))
        except Site.DoesNotExist:
            site = Site.objects.create(id=settings.SITE_ID, domain=domain, name=site_name)
            self.stdout.write(self.style.SUCCESS(f'   ✓ Site created: {domain}'))

        # Step 2: Check Google OAuth credentials
        self.stdout.write('\n2. Checking Google OAuth credentials...')
        client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '')
        client_secret = getattr(settings, 'GOOGLE_CLIENT_SECRET', '')

        if not client_id or not client_secret:
            self.stdout.write(self.style.ERROR('   ✗ Google OAuth credentials not found in settings!'))
            self.stdout.write(self.style.WARNING('\n   Please add to your .env file:'))
            self.stdout.write('   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com')
            self.stdout.write('   GOOGLE_CLIENT_SECRET=your-client-secret')
            self.stdout.write(self.style.WARNING('\n   See GOOGLE_OAUTH_SETUP.md for detailed instructions.'))
            return

        self.stdout.write(self.style.SUCCESS(f'   ✓ Client ID found: {client_id[:20]}...'))
        self.stdout.write(self.style.SUCCESS('   ✓ Client Secret found'))

        # Step 3: Create or update SocialApp
        self.stdout.write('\n3. Configuring Social Application...')
        try:
            social_app = SocialApp.objects.get(provider='google')
            social_app.name = 'Google OAuth'
            social_app.client_id = client_id
            social_app.secret = client_secret
            social_app.save()
            self.stdout.write(self.style.SUCCESS('   ✓ Social Application updated'))
        except SocialApp.DoesNotExist:
            social_app = SocialApp.objects.create(
                provider='google',
                name='Google OAuth',
                client_id=client_id,
                secret=client_secret,
            )
            self.stdout.write(self.style.SUCCESS('   ✓ Social Application created'))

        # Link to site
        if site not in social_app.sites.all():
            social_app.sites.add(site)
            self.stdout.write(self.style.SUCCESS(f'   ✓ Linked to site: {domain}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'   ✓ Already linked to site: {domain}'))

        # Step 4: Display configuration summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('Google OAuth Setup Complete!'))
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write('\nConfiguration Summary:')
        self.stdout.write(f'  Site Domain: {domain}')
        self.stdout.write(f'  Site Name: {site_name}')
        self.stdout.write(f'  Provider: Google')
        self.stdout.write(f'  Client ID: {client_id[:30]}...')
        
        self.stdout.write('\nAuthorized Redirect URIs (add these to Google Cloud Console):')
        self.stdout.write(f'  http://{domain}/accounts/google/login/callback/')
        if domain == 'localhost:8000':
            self.stdout.write('  http://127.0.0.1:8000/accounts/google/login/callback/')
        
        self.stdout.write('\nAuthorized JavaScript Origins:')
        self.stdout.write(f'  http://{domain}')
        if domain == 'localhost:8000':
            self.stdout.write('  http://127.0.0.1:8000')

        self.stdout.write('\nNext Steps:')
        self.stdout.write('  1. Ensure redirect URIs are configured in Google Cloud Console')
        self.stdout.write('  2. Start your server: python manage.py runserver')
        self.stdout.write('  3. Visit: http://localhost:8000/login/')
        self.stdout.write('  4. Click "Continue with Google" to test')
        
        self.stdout.write(self.style.SUCCESS('\n✓ Setup complete!'))
