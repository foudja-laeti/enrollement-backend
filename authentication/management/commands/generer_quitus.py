from django.core.management.base import BaseCommand, CommandError
from authentication.models import CodeQuitus

class Command(BaseCommand):
    help = 'Génère des codes quitus pour la banque'

    def add_arguments(self, parser):
        parser.add_argument(
            'nombre',
            type=int,
            help='Nombre de codes à générer'
        )
        parser.add_argument(
            '--montant',
            type=int,
            default=50000,
            help='Montant en FCFA (défaut: 50000)'
        )
        parser.add_argument(
            '--validite',
            type=int,
            default=90,
            help='Durée de validité en jours (défaut: 90)'
        )

    def handle(self, *args, **options):
        nombre = options['nombre']
        montant = options['montant']
        validite = options['validite']
        
        if nombre <= 0:
            raise CommandError('Le nombre doit être supérieur à 0')
        
        if nombre > 10000:
            self.stdout.write(
                self.style.WARNING(
                    f'⚠️  Attention: Génération de {nombre} codes (cela peut prendre du temps)...'
                )
            )
        
        self.stdout.write(f'🔄 Génération de {nombre} codes quitus...')
        self.stdout.write(f'   Montant: {montant:,.0f} FCFA')
        self.stdout.write(f'   Validité: {validite} jours\n')
        
        try:
            codes = CodeQuitus.generer_batch(
                nombre=nombre,
                montant=montant,
                validite_jours=validite
            )
            
            self.stdout.write(self.style.SUCCESS(f'✅ {len(codes)} codes générés avec succès !\n'))
            
            # Afficher les 10 premiers codes
            self.stdout.write(self.style.WARNING('📋 Premiers codes générés:'))
            for code in codes[:10]:
                self.stdout.write(
                    f'   • Code: {self.style.SUCCESS(code.code)} | '
                    f'Ref: {code.reference_bancaire} | '
                    f'Montant: {code.montant:,.0f} FCFA'
                )
            
            if len(codes) > 10:
                self.stdout.write(f'\n   ... et {len(codes) - 10} autres codes')
            
            # Informations de validité
            self.stdout.write(
                self.style.WARNING(
                    f'\n⏰ Validité: Ces codes expirent le {codes[0].date_expiration.strftime("%d/%m/%Y à %H:%M")}'
                )
            )
            
            # Statistiques
            total_codes = CodeQuitus.objects.count()
            codes_utilises = CodeQuitus.objects.filter(utilise=True).count()
            codes_disponibles = CodeQuitus.objects.filter(utilise=False).count()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n📊 Statistiques totales:'
                    f'\n   • Total codes: {total_codes}'
                    f'\n   • Disponibles: {codes_disponibles}'
                    f'\n   • Utilisés: {codes_utilises}'
                )
            )
            
        except Exception as e:
            raise CommandError(f'Erreur lors de la génération: {str(e)}')