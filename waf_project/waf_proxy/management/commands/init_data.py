from django.core.management.base import BaseCommand
from waf_proxy.models import User, Site, Rule, SiteRule

class Command(BaseCommand):
    help = 'Initialize WAF with demo data'

    def handle(self, *args, **options):
        self.stdout.write('Creating demo users...')
        
        # Create admin user
        admin_user, created = User.objects.get_or_create(
            email='admin@waf.com',
            defaults={
                'user_type': 'admin',
                'admin_level': 'super',
                'is_active': True
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('Admin user created'))
        else:
            self.stdout.write('Admin user already exists')
        
        # Create customer user
        customer_user, created = User.objects.get_or_create(
            email='customer@waf.com',
            defaults={
                'user_type': 'customer',
                'company_name': 'Demo Company',
                'phone': '+1-555-0123',
                'is_active': True
            }
        )
        if created:
            customer_user.set_password('customer123')
            customer_user.save()
            self.stdout.write(self.style.SUCCESS('Customer user created'))
        else:
            self.stdout.write('Customer user already exists')
        
        # Create demo site
        demo_site, created = Site.objects.get_or_create(
            domain='http://demo.example.com',
            defaults={
                'owner': customer_user,
                'backend_url': 'http://backend.example.com',
                'is_active': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Demo site created'))
        else:
            self.stdout.write('Demo site already exists')
        
        # Create default rules
        rules_data = [
            {
                'name': 'SQL Injection Protection',
                'pattern': 'union select|drop table|delete from|insert into|update set|--|/\\*.*\\*/|xp_cmdshell|sp_executesql',
                'rule_type': 'sql_injection',
                'action': 'BLOCK',
                'description': 'Blocks common SQL injection patterns'
            },
            {
                'name': 'XSS Protection',
                'pattern': '<script[^>]*>|javascript:|onload\\s*=|onerror\\s*=|onclick\\s*=|<iframe[^>]*>|<object[^>]*>|<embed[^>]*>',
                'rule_type': 'xss',
                'action': 'BLOCK',
                'description': 'Blocks cross-site scripting attacks'
            },
            {
                'name': 'Path Traversal Protection',
                'pattern': '\\.\\./|\\.\\.\\\\|/etc/passwd|/etc/shadow|/windows/system32|\\.\\.%2f|\\.\\.%5c',
                'rule_type': 'path_traversal',
                'action': 'BLOCK',
                'description': 'Prevents directory traversal attacks'
            },
            {
                'name': 'Bot Detection',
                'pattern': 'bot|crawler|spider|scraper|curl|wget|python-requests',
                'rule_type': 'bot_detection',
                'action': 'LOG',
                'description': 'Detects and logs bot traffic'
            },
            {
                'name': 'Rate Limiting',
                'pattern': 'rate_limit',
                'rule_type': 'rate_limit',
                'action': 'BLOCK',
                'description': 'Limits requests per IP address'
            }
        ]
        
        for rule_data in rules_data:
            rule, created = Rule.objects.get_or_create(
                name=rule_data['name'],
                defaults=rule_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Rule "{rule.name}" created'))
            else:
                self.stdout.write(f'Rule "{rule.name}" already exists')
        
        # Add rules to demo site
        for rule in Rule.objects.all():
            site_rule, created = SiteRule.objects.get_or_create(
                site=demo_site,
                rule=rule,
                defaults={'is_active': True}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Rule "{rule.name}" added to demo site'))
        
        self.stdout.write(self.style.SUCCESS('Demo data initialization completed!'))
        self.stdout.write('Demo credentials:')
        self.stdout.write('Admin: admin@waf.com / admin123')
        self.stdout.write('Customer: customer@waf.com / customer123')
