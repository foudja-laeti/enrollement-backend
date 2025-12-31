# api/management/commands/generer_quitus.py
from django.core.management.base import BaseCommand
from api.models import CodeQuitus

class Command(BaseCommand):
    help = 'Génère des codes quitus pour la banque'

    def add_arguments(self, parser):
        parser.add_argument(
            'nombre', 
            type=int, 
            help='Nombre de codes à générer'
        )

    def handle(self, *args, **options):
        nombre = options['nombre']
        
        self.stdout.write(f'🔄 Génération de {nombre} codes quitus en cours...')
        
        try:
            codes = CodeQuitus.generer_batch(nombre)
            
            self.stdout.write(self.style.SUCCESS(
                f'\n✅ {len(codes)} codes générés avec succès !\n'
            ))
            
            self.stdout.write('📋 Exemples de codes générés:')
            for code in codes[:10]:
                self.stdout.write(
                    f'  • Code: {code.code} | Ref: {code.reference_bancaire} | Montant: {code.montant} FCFA'
                )
            
            if len(codes) > 10:
                self.stdout.write(f'\n... et {len(codes) - 10} autres codes\n')
            
            self.stdout.write(self.style.WARNING(
                f'\n⚠️  Ces codes sont valables jusqu\'au {codes[0].date_expiration.strftime("%d/%m/%Y")}'
            ))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Erreur: {str(e)}'))