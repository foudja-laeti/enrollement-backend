# candidats/management/commands/duplicate_candidat.py
# Créez ce fichier dans: candidats/management/commands/

from django.core.management.base import BaseCommand
from candidats.models import Candidat, Dossier, Document
from django.core.files.base import ContentFile
import random
import string

class Command(BaseCommand):
    help = 'Duplique un candidat existant pour les tests'

    def add_arguments(self, parser):
        parser.add_argument('matricule', type=str, help='Matricule du candidat à dupliquer')
        parser.add_argument('--count', type=int, default=1, help='Nombre de duplications')

    def handle(self, *args, **options):
        matricule = options['matricule']
        count = options['count']
        
        try:
            # Récupérer le candidat source
            candidat_source = Candidat.objects.get(matricule=matricule)
            self.stdout.write(self.style.SUCCESS(f'✅ Candidat source trouvé: {candidat_source.matricule}'))
            
            # Récupérer le dossier source
            dossier_source = Dossier.objects.filter(candidat=candidat_source).first()
            
            for i in range(count):
                # Générer un nouveau matricule
                random_suffix = ''.join(random.choices(string.digits, k=5))
                nouveau_matricule = f'CAND2026{random_suffix}'
                
                # Dupliquer le candidat
                nouveau_candidat = Candidat.objects.create(
                    matricule=nouveau_matricule,
                    nom=candidat_source.nom,
                    prenom=f"{candidat_source.prenom} {i+1}",  # Différencier les prénoms
                    email=f"test{random_suffix}@example.com",
                    telephone=candidat_source.telephone,
                    telephone_secondaire=candidat_source.telephone_secondaire,
                    date_naissance=candidat_source.date_naissance,
                    lieu_naissance=candidat_source.lieu_naissance,
                    sexe=candidat_source.sexe,
                    ville=candidat_source.ville,
                    quartier=candidat_source.quartier,
                    adresse_actuelle=candidat_source.adresse_actuelle,
                    region=candidat_source.region,
                    departement=candidat_source.departement,
                    nom_pere=candidat_source.nom_pere,
                    tel_pere=candidat_source.tel_pere,
                    nom_mere=candidat_source.nom_mere,
                    tel_mere=candidat_source.tel_mere,
                    bac=candidat_source.bac,
                    serie=candidat_source.serie,
                    mention=candidat_source.mention,
                    filiere=candidat_source.filiere,
                    niveau=candidat_source.niveau,
                    centre_examen=candidat_source.centre_examen,
                    centre_depot=candidat_source.centre_depot,
                    etablissement_origine=candidat_source.etablissement_origine,
                    annee_obtention_diplome=candidat_source.annee_obtention_diplome,
                    statut_dossier='complet',  # Directement complet
                )
                
                # Copier la photo
                if candidat_source.photo:
                    photo_content = candidat_source.photo.read()
                    nouveau_candidat.photo.save(
                        f'{nouveau_matricule}_photo.png',
                        ContentFile(photo_content),
                        save=True
                    )
                
                self.stdout.write(self.style.SUCCESS(f'✅ Candidat créé: {nouveau_matricule}'))
                
                # Dupliquer le dossier
                if dossier_source:
                    nouveau_dossier = Dossier.objects.create(
                        candidat=nouveau_candidat,
                        numero_dossier=f'DOS{nouveau_candidat.id}-2026',
                        date_creation=dossier_source.date_creation,
                        statut='complet',
                    )
                    self.stdout.write(self.style.SUCCESS(f'  📁 Dossier créé: {nouveau_dossier.numero_dossier}'))
                    
                    # Dupliquer les documents
                    documents_source = Document.objects.filter(dossier=dossier_source)
                    for doc_source in documents_source:
                        if doc_source.fichier:
                            fichier_content = doc_source.fichier.read()
                            nouveau_doc = Document.objects.create(
                                dossier=nouveau_dossier,
                                type=doc_source.type,
                                nom=doc_source.nom,
                            )
                            nouveau_doc.fichier.save(
                                f'{nouveau_matricule}_{doc_source.type}.png',
                                ContentFile(fichier_content),
                                save=True
                            )
                            self.stdout.write(self.style.SUCCESS(f'  📄 Document créé: {doc_source.type}'))
            
            self.stdout.write(self.style.SUCCESS(f'\n🎉 {count} candidat(s) dupliqué(s) avec succès!'))
            
        except Candidat.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ Candidat {matricule} non trouvé'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Erreur: {e}'))
            import traceback
            traceback.print_exc()