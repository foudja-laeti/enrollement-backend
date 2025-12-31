# authentication/management/commands/create_superadmin.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()


class Command(BaseCommand):
    help = 'Créer un super administrateur'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Email du super admin')
        parser.add_argument('--password', type=str, help='Mot de passe')
        parser.add_argument('--nom', type=str, help='Nom')
        parser.add_argument('--prenom', type=str, help='Prénom')
        parser.add_argument('--non-interactive', action='store_true', help='Mode non interactif')

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('   CRÉATION D\'UN SUPER ADMINISTRATEUR'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))

        # Mode non-interactif
        if options['non_interactive']:
            email = options.get('email')
            password = options.get('password')
            nom = options.get('nom')
            prenom = options.get('prenom')
            
            if not all([email, password, nom, prenom]):
                self.stdout.write(self.style.ERROR(
                    '❌ En mode non-interactif, tous les arguments sont requis: '
                    '--email --password --nom --prenom'
                ))
                return
        else:
            # Mode interactif
            email = options.get('email') or input('📧 Email: ')
            
            # Validation email
            while not email or '@' not in email:
                self.stdout.write(self.style.ERROR('❌ Email invalide'))
                email = input('📧 Email: ')
            
            # Vérifier si l'email existe déjà
            if User.objects.filter(email=email).exists():
                self.stdout.write(self.style.ERROR(
                    f'❌ Un utilisateur avec l\'email {email} existe déjà'
                ))
                return
            
            password = options.get('password') or input('🔒 Mot de passe: ')
            while len(password) < 8:
                self.stdout.write(self.style.ERROR('❌ Le mot de passe doit contenir au moins 8 caractères'))
                password = input('🔒 Mot de passe: ')
            
            password_confirm = input('🔒 Confirmer le mot de passe: ')
            while password != password_confirm:
                self.stdout.write(self.style.ERROR('❌ Les mots de passe ne correspondent pas'))
                password = input('🔒 Mot de passe: ')
                password_confirm = input('🔒 Confirmer le mot de passe: ')
            
            nom = options.get('nom') or input('👤 Nom: ')
            prenom = options.get('prenom') or input('👤 Prénom: ')

        try:
            user = User.objects.create_superuser(
                email=email,
                password=password,
                nom=nom,
                prenom=prenom,
                is_email_verified=True
            )

            self.stdout.write(self.style.SUCCESS('\n' + '='*60))
            self.stdout.write(self.style.SUCCESS('✅ SUPER ADMINISTRATEUR CRÉÉ AVEC SUCCÈS!'))
            self.stdout.write(self.style.SUCCESS('='*60))
            self.stdout.write(f'   📧 Email       : {user.email}')
            self.stdout.write(f'   👤 Nom         : {user.nom}')
            self.stdout.write(f'   👤 Prénom      : {user.prenom}')
            self.stdout.write(f'   🎭 Rôle        : {user.get_role_display_custom()}')
            self.stdout.write(f'   🆔 ID          : {user.id}')
            self.stdout.write(f'   ✅ Actif       : {user.is_active}')
            self.stdout.write(f'   ✅ Vérifié     : {user.is_email_verified}')
            self.stdout.write(self.style.SUCCESS('='*60))
            self.stdout.write(self.style.SUCCESS('\n💡 Utilisez ces identifiants pour vous connecter\n'))

        except IntegrityError:
            self.stdout.write(self.style.ERROR(
                f'\n❌ Erreur: Un utilisateur avec l\'email {email} existe déjà\n'
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Erreur lors de la création: {str(e)}\n'))