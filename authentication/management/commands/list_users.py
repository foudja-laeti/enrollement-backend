# authentication/management/commands/list_users.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Lister tous les utilisateurs du système'

    def add_arguments(self, parser):
        parser.add_argument(
            '--role',
            type=str,
            help='Filtrer par rôle (super_admin, admin_academique, responsable_filiere, candidat)'
        )
        parser.add_argument(
            '--active-only',
            action='store_true',
            help='Afficher uniquement les utilisateurs actifs'
        )

    def handle(self, *args, **options):
        users = User.objects.all().order_by('role', 'email')
        
        if options['role']:
            users = users.filter(role=options['role'])
        
        if options['active_only']:
            users = users.filter(is_active=True)

        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('   LISTE DES UTILISATEURS'))
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))

        if not users.exists():
            self.stdout.write(self.style.WARNING('   Aucun utilisateur trouvé\n'))
            return

        # Grouper par rôle
        roles = {}
        for user in users:
            if user.role not in roles:
                roles[user.role] = []
            roles[user.role].append(user)

        for role, users_list in roles.items():
            role_display = dict(User.ROLE_CHOICES).get(role, role)
            self.stdout.write(self.style.SUCCESS(f'\n   {role_display.upper()} ({len(users_list)})'))
            self.stdout.write('   ' + '-'*76)
            
            for user in users_list:
                status = '✅' if user.is_active else '❌'
                verified = '✓' if user.is_email_verified else '✗'
                full_name = user.get_full_name()
                
                self.stdout.write(
                    f'   {status} [{user.id:3d}] {user.email:40s} | {full_name:25s} | Vérifié: {verified}'
                )

        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(f'   Total: {users.count()} utilisateurs')
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))