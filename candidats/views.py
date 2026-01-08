# candidats/views.py
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes, parser_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q
from django.utils import timezone
from candidats.utils.pdf_generator import generer_fiche_enrollement
from django.core.mail import EmailMessage
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import qrcode
from io import BytesIO
import base64
from .utils.pdf_generator import generer_fiche_enrollement
from .models import Candidat, Dossier, Document
from .serializers import (
    CandidatEnrollementSerializer,
    CandidatListSerializer,
    CandidatDetailSerializer,
    DossierValidationSerializer
)
from .permissions import IsResponsableFiliere
from authentication.models import CodeQuitus
from configurations.models import Filiere


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def enrollement_view(request):
    """Compléter profil candidat - USER AUTHENTIFIÉ"""
    
    user = request.user
    print(f"\n{'='*80}")
    print(f"👤 USER AUTHENTIFIÉ: {user.email} (role: {user.role})")
    print(f"{'='*80}")
    
    # ✅ 1. VÉRIFIER RÔLE
    if user.role != 'candidat':
        print("❌ User n'est pas candidat")
        return Response({
            'error': 'Accès refusé',
            'message': 'Seuls les candidats peuvent accéder à cette fonctionnalité.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # ✅ 2. LOG STATUT ACTUEL
    try:
        candidat_existant = Candidat.objects.get(user=user)
        print(f"📋 Candidat existant: {candidat_existant.matricule} | Statut: {candidat_existant.statut_dossier}")
    except Candidat.DoesNotExist:
        print("📋 Aucun candidat trouvé")
    
    # ✅ 3. DEBUG FICHIERS (CRITIQUE)
    print(f"\n📂 FICHIERS REÇUS ({len(request.FILES)}):")
    for key in request.FILES.keys():
        file = request.FILES[key]
        print(f"  ✅ {key}: {file.name} ({file.size} bytes)")
    
    print(f"\n📥 DONNÉES ({len(request.data)}):")
    for key, value in request.data.items():
        print(f"  📝 {key}: {value}")
    
    # 🔥 FIX : COMBINER request.data + request.FILES
    data = request.data.copy()  # Copie mutable
    for key, file in request.FILES.items():
        data[key] = file  # Ajoute les fichiers !
    
    print(f"\n🔗 DATA+FICHIERS ({len(data)} champs):")
    for key in data.keys():
        print(f"  ✅ {key}: {'FILE' if hasattr(data[key], 'name') else data[key]}")
    
    # ✅ 4. VALIDATION SERIALIZER
    serializer = CandidatEnrollementSerializer(data=data, context={'request': request})
    
    print(f"\n🔍 VALIDATION...")
    if serializer.is_valid():
        print("✅ VALIDATION OK")
        
        try:
            print(f"\n💾 SAUVEGARDE...")
            candidat = serializer.save()
            print(f"✅ SUCCÈS: {candidat.matricule} | Statut: {candidat.statut_dossier}")
            
            return Response({
                'success': True,
                'message': 'Enrôlement réussi ! Votre dossier est complet.',
                'candidat': {
                    'matricule': candidat.matricule,
                    'nom_complet': f'{candidat.nom} {candidat.prenom}',
                    'statut_dossier': candidat.statut_dossier,
                },
                'next_steps': [
                    'Votre dossier a été soumis avec succès',
                    'Consultez votre tableau de bord pour suivre l\'état'
                ]
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            print(f"❌ ERREUR SAUVEGARDE: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({
                'error': 'Erreur sauvegarde',
                'message': str(e),
                'support': 'support@estlc.cm'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # ❌ ERREURS
    print(f"❌ ERREURS: {serializer.errors}")
    return Response({
        'error': 'Données invalides',
        'details': serializer.errors,
        'message': 'Veuillez corriger les erreurs indiquées.'
    }, status=status.HTTP_400_BAD_REQUEST)
# candidats/views.py - ResponsableFiliereViewSet COMPLET ET CORRIGÉ

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Count, Avg, Q
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import send_mail
from authentication.permissions import IsResponsableFiliere
from .models import Candidat, Document
import csv
import qrcode
import base64
from io import BytesIO
from datetime import date, timedelta

class ResponsableFiliereViewSet(viewsets.ViewSet):
    """ViewSet pour les responsables de filière"""
    permission_classes = [IsAuthenticated, IsResponsableFiliere]
    
    @action(detail=False, methods=['get'], url_path='dashboard-stats')
    def dashboard_stats(self, request):
        """Statistiques du tableau de bord du RF"""
        try:
            user = request.user
            rf_profile = user.responsable_filiere_profile
            filiere = rf_profile.filiere
            
            print(f"📊 Chargement stats pour {user.email} - Filière: {filiere.libelle}")
            
            # Candidats de la filière
            candidats_filiere = Candidat.objects.filter(filiere=filiere)
            total = candidats_filiere.count()
            
            # Statistiques des dossiers
            valides = candidats_filiere.filter(statut_dossier='valide').count()
            complets = candidats_filiere.filter(statut_dossier='complet').count()
            en_attente = candidats_filiere.filter(statut_dossier='en_attente').count()
            rejetes = candidats_filiere.filter(statut_dossier='rejete').count()
            actifs = candidats_filiere.filter(user__is_active=True).count()
            
            # Calculs
            taux_validation = round((valides / total) * 100, 2) if total > 0 else 0
            taux_inscription = round(((valides + complets) / total) * 100, 2) if total > 0 else 0
            
            stats = {
                'candidats_total': total,
                'candidats_actifs': actifs,
                'candidats_filiere': total,
                'taux_inscription': taux_inscription,
                'dossiers_en_attente': en_attente,
                'dossiers_complets': complets,
                'dossiers_valides': valides,
                'dossiers_rejetes': rejetes,
                'taux_validation': taux_validation,
                'filiere': {
                    'id': filiere.id,
                    'code': filiere.code,
                    'libelle': filiere.libelle,
                    'nom': filiere.libelle,
                    'quota': filiere.quota if hasattr(filiere, 'quota') else None,
                    'capacite': filiere.quota if hasattr(filiere, 'quota') else None,
                }
            }
            
            print(f"✅ Stats: Total={total}, Validés={valides}, Complets={complets}")
            return Response(stats)
            
        except AttributeError as e:
            print(f"❌ Erreur AttributeError: {e}")
            return Response(
                {'error': 'Profil responsable de filière non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(f"❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='mes-candidats')
    def mes_candidats(self, request):
        """Liste des candidats de la filière du RF avec filtres"""
        try:
            user = request.user
            rf_profile = user.responsable_filiere_profile
            filiere = rf_profile.filiere
            
            print(f"👥 Chargement candidats pour filière: {filiere.libelle}")
            
            # Filtres
            statut = request.query_params.get('statut', None)
            search = request.query_params.get('search', None)
            
            # Query de base
            candidats = Candidat.objects.filter(filiere=filiere).select_related(
                'user', 'bac', 'serie', 'mention', 'niveau',
                'centre_examen', 'centre_depot'
            )
            
            # Filtrer par statut
            if statut:
                candidats = candidats.filter(statut_dossier=statut)
            
            # Recherche
            if search:
                candidats = candidats.filter(
                    Q(nom__icontains=search) |
                    Q(prenom__icontains=search) |
                    Q(matricule__icontains=search) |
                    Q(email__icontains=search)
                )
            
            # Pagination
            page = int(request.query_params.get('page', 1))
            per_page = int(request.query_params.get('per_page', 20))
            start = (page - 1) * per_page
            end = start + per_page
            
            total = candidats.count()
            candidats_page = candidats.order_by('-created_at')[start:end]
            
            # Construire la réponse manuellement
            results = []
            for candidat in candidats_page:
                results.append({
                    'id': candidat.id,
                    'matricule': candidat.matricule,
                    'nom': candidat.nom,
                    'prenom': candidat.prenom,
                    'email': candidat.email,
                    'telephone': candidat.telephone,
                    'statut_dossier': candidat.statut_dossier,
                    'date_naissance': candidat.date_naissance,
                    'sexe': candidat.sexe,
                    'serie': {
                        'id': candidat.serie.id,
                        'libelle': candidat.serie.libelle
                    } if candidat.serie else None,
                    'mention': {
                        'id': candidat.mention.id,
                        'libelle': candidat.mention.libelle
                    } if candidat.mention else None,
                    'created_at': candidat.created_at,
                    'updated_at': candidat.updated_at,
                })
            
            print(f"✅ {len(results)} candidats trouvés")
            
            return Response({
                'results': results,
                'count': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page
            })
            
        except Exception as e:
            print(f"❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], url_path='candidat-detail')
    def candidat_detail(self, request, pk=None):
        """Détails complets d'un candidat"""
        try:
            user = request.user
            rf_profile = user.responsable_filiere_profile
            
            # Vérifier que le candidat appartient à la filière du RF
            candidat = Candidat.objects.select_related(
                'user', 'region', 'departement', 'bac', 'serie',
                'mention', 'filiere', 'niveau', 'centre_examen', 'centre_depot'
            ).get(
                id=pk,
                filiere=rf_profile.filiere
            )
            
            # Récupérer les documents
            documents = Document.objects.filter(candidat=candidat)
            
            # Construire la réponse
            data = {
                'id': candidat.id,
                'matricule': candidat.matricule,
                'nom': candidat.nom,
                'prenom': candidat.prenom,
                'email': candidat.email,
                'telephone': candidat.telephone,
                'telephone_secondaire': candidat.telephone_secondaire,
                'date_naissance': candidat.date_naissance,
                'lieu_naissance': candidat.lieu_naissance,
                'sexe': candidat.sexe,
                'ville': candidat.ville,
                'quartier': candidat.quartier,
                'adresse_actuelle': candidat.adresse_actuelle,
                'statut_dossier': candidat.statut_dossier,
                
                # Parents
                'nom_pere': candidat.nom_pere,
                'tel_pere': candidat.tel_pere,
                'nom_mere': candidat.nom_mere,
                'tel_mere': candidat.tel_mere,
                
                # Localisation
                'region': {
                    'id': candidat.region.id,
                    'nom': candidat.region.nom
                } if candidat.region else None,
                'departement': {
                    'id': candidat.departement.id,
                    'nom': candidat.departement.nom
                } if candidat.departement else None,
                
                # Académique
                'bac': {
                    'id': candidat.bac.id,
                    'libelle': candidat.bac.libelle
                } if candidat.bac else None,
                'serie': {
                    'id': candidat.serie.id,
                    'libelle': candidat.serie.libelle
                } if candidat.serie else None,
                'mention': {
                    'id': candidat.mention.id,
                    'libelle': candidat.mention.libelle
                } if candidat.mention else None,
                'filiere': {
                    'id': candidat.filiere.id,
                    'code': candidat.filiere.code,
                    'libelle': candidat.filiere.libelle
                } if candidat.filiere else None,
                'niveau': {
                    'id': candidat.niveau.id,
                    'libelle': candidat.niveau.libelle
                } if candidat.niveau else None,
                'centre_examen': {
                    'id': candidat.centre_examen.id,
                    'nom': candidat.centre_examen.nom
                } if candidat.centre_examen else None,
                'centre_depot': {
                    'id': candidat.centre_depot.id,
                    'nom': candidat.centre_depot.nom
                } if candidat.centre_depot else None,
                'etablissement_origine': candidat.etablissement_origine,
                'annee_obtention_diplome': candidat.annee_obtention_diplome,
                
                # Photo
                'photo_url': request.build_absolute_uri(
                    settings.MEDIA_URL + candidat.photo_path
                ) if candidat.photo_path else None,
                
                # Documents
                'documents': [
                    {
                        'id': doc.id,
                        'type': doc.type_document,
                        'nom': doc.nom_fichier,
                        'url': request.build_absolute_uri(
                            settings.MEDIA_URL + doc.chemin_fichier
                        ),
                        'is_verified': doc.is_verified,
                        'verified_at': doc.verified_at,
                        'commentaire': doc.commentaire_verification
                    }
                    for doc in documents
                ],
                
                'created_at': candidat.created_at,
                'updated_at': candidat.updated_at
            }
            
            return Response(data)
            
        except Candidat.DoesNotExist:
            return Response(
                {'error': 'Candidat non trouvé ou non autorisé'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='profil-filiere')
    def profil_filiere(self, request):
        """Informations détaillées sur la filière du RF"""
        try:
            user = request.user
            rf_profile = user.responsable_filiere_profile
            filiere = rf_profile.filiere
            
            print(f"📋 Chargement profil filière: {filiere.libelle}")
            
            # Candidats de la filière
            candidats_filiere = Candidat.objects.filter(filiere=filiere)
            candidats_valides = candidats_filiere.filter(statut_dossier='valide')
            
            # Répartition par série
            repartition_serie = list(
                candidats_valides.values('serie__libelle')
                .annotate(total=Count('id'))
                .order_by('-total')
            )
            
            # Répartition par mention
            repartition_mention = list(
                candidats_valides.values('mention__libelle')
                .annotate(total=Count('id'))
                .order_by('-total')
            )
            
            # Évolution mensuelle (6 derniers mois)
            today = timezone.now()
            evolution = []
            for i in range(6):
                mois_date = today - timedelta(days=30*i)
                debut_mois = mois_date.replace(day=1)
                fin_mois = (debut_mois + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                
                count = candidats_valides.filter(
                    date_validation__gte=debut_mois,
                    date_validation__lte=fin_mois
                ).count() if hasattr(Candidat, 'date_validation') else 0
                
                evolution.insert(0, {
                    'mois': debut_mois.strftime('%B'),
                    'total': count
                })
            
            # Âge moyen
            ages = []
            for c in candidats_valides.filter(date_naissance__isnull=False):
                age = (date.today() - c.date_naissance).days / 365.25
                ages.append(age)
            age_moyen = round(sum(ages) / len(ages), 1) if ages else None
            
            # Calcul places restantes et taux de remplissage
            quota = filiere.quota if hasattr(filiere, 'quota') else None
            places_restantes = max(0, quota - candidats_valides.count()) if quota else 0
            taux_remplissage = round((candidats_valides.count() / quota) * 100, 2) if quota and quota > 0 else 0
            
            data = {
                'id': filiere.id,
                'code': filiere.code,
                'libelle': filiere.libelle,
                'description': filiere.description if hasattr(filiere, 'description') else None,
                'quota': quota,
                'places_restantes': places_restantes,
                'taux_remplissage': taux_remplissage,
                
                # Statistiques avancées
                'statistiques': {
                    'total_candidats': candidats_filiere.count(),
                    'candidats_valides': candidats_valides.count(),
                    'candidats_en_attente': candidats_filiere.filter(statut_dossier__in=['en_attente', 'complet']).count(),
                    'candidats_rejetes': candidats_filiere.filter(statut_dossier='rejete').count(),
                    'age_moyen': age_moyen,
                    'repartition_serie': repartition_serie,
                    'repartition_mention': repartition_mention,
                    'evolution_mensuelle': evolution,
                },
                
                # Responsable
                'responsable': {
                    'nom': user.nom,
                    'prenom': user.prenom,
                    'email': user.email,
                    'telephone': rf_profile.telephone
                }
            }
            
            print(f"✅ Profil chargé avec {data['statistiques']['total_candidats']} candidats")
            return Response(data)
            
        except Exception as e:
            print(f"❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='export-stats')
    def export_stats(self, request):
        """Exporter les statistiques complètes en CSV"""
        try:
            user = request.user
            rf_profile = user.responsable_filiere_profile
            filiere = rf_profile.filiere
            
            # Créer la réponse CSV
            response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
            response['Content-Disposition'] = f'attachment; filename="statistiques_{filiere.code}_{timezone.now().date()}.csv"'
            
            writer = csv.writer(response)
            
            # En-tête principal
            writer.writerow(['STATISTIQUES DÉTAILLÉES'])
            writer.writerow(['Filière', filiere.libelle])
            writer.writerow(['Code', filiere.code])
            writer.writerow(['Date d\'export', timezone.now().strftime('%d/%m/%Y %H:%M')])
            writer.writerow([])
            
            # Section: Vue d'ensemble
            writer.writerow(['=== VUE D\'ENSEMBLE ==='])
            writer.writerow(['Métrique', 'Valeur'])
            
            candidats_filiere = Candidat.objects.filter(filiere=filiere)
            total = candidats_filiere.count()
            valides = candidats_filiere.filter(statut_dossier='valide').count()
            complets = candidats_filiere.filter(statut_dossier='complet').count()
            en_attente = candidats_filiere.filter(statut_dossier='en_attente').count()
            rejetes = candidats_filiere.filter(statut_dossier='rejete').count()
            
            writer.writerow(['Total candidats', total])
            writer.writerow(['Dossiers validés', valides])
            writer.writerow(['Dossiers complets', complets])
            writer.writerow(['Dossiers en attente', en_attente])
            writer.writerow(['Dossiers rejetés', rejetes])
            writer.writerow(['Taux de validation', f'{round((valides/total)*100, 2) if total > 0 else 0}%'])
            writer.writerow([])
            
            # Section: Liste des candidats validés
            writer.writerow(['=== CANDIDATS VALIDÉS ==='])
            writer.writerow([
                'Matricule', 'Nom', 'Prénom', 'Email', 'Téléphone',
                'Sexe', 'Date naissance', 'Série', 'Mention'
            ])
            
            candidats_valides = candidats_filiere.filter(
                statut_dossier='valide'
            ).select_related('serie', 'mention')
            
            for candidat in candidats_valides:
                writer.writerow([
                    candidat.matricule or 'N/A',
                    candidat.nom,
                    candidat.prenom,
                    candidat.email,
                    candidat.telephone or 'N/A',
                    candidat.sexe or 'N/A',
                    candidat.date_naissance.strftime('%d/%m/%Y') if candidat.date_naissance else 'N/A',
                    candidat.serie.libelle if candidat.serie else 'N/A',
                    candidat.mention.libelle if candidat.mention else 'N/A',
                ])
            
            return response
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='valider-dossier')
    def valider_dossier(self, request, pk=None):
        """Valider le dossier d'un candidat"""
        print("\n" + "="*80)
        print("🚀 DÉBUT VALIDATION")
        print("="*80)
        
        try:
            print("1️⃣ Récupération user...")
            user = request.user
            print(f"   User: {user.email}")
            
            print("2️⃣ Récupération profil RF...")
            rf_profile = user.responsable_filiere_profile
            print(f"   RF Filière: {rf_profile.filiere.libelle}")
            
            print(f"3️⃣ Recherche candidat ID={pk}...")
            candidat = Candidat.objects.get(
                id=pk,
                filiere=rf_profile.filiere
            )
            print(f"   ✅ Candidat trouvé: {candidat.matricule}")
            print(f"   Statut: {candidat.statut_dossier}")
            
            if candidat.statut_dossier != 'complet':
                print(f"   ❌ Statut invalide!")
                return Response(
                    {'error': 'Le dossier doit être complet pour être validé'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            print("4️⃣ Mise à jour statut en BD...")
            candidat.statut_dossier = 'valide'
            candidat.date_validation = timezone.now()
            if hasattr(candidat, 'valide_par'):
                candidat.valide_par = user
            candidat.save()
            print("   ✅ Statut sauvegardé en BD")
            
            print("5️⃣ DÉBUT GÉNÉRATION EMAIL...")
            try:
                print("   📄 Import pdf_generator...")
                from candidats.utils.pdf_generator import generer_fiche_enrollement
                print("   ✅ Import OK")
                
                print("   📄 Appel generer_fiche_enrollement()...")
                pdf_buffer = generer_fiche_enrollement(candidat)
                print("   ✅ Fonction retournée")
                
                print("   📦 Lecture contenu PDF...")
                pdf_size = len(pdf_buffer.getvalue())
                print(f"   ✅ PDF: {pdf_size} octets")
                
                if pdf_size == 0:
                    print("   ❌ PDF VIDE!")
                    raise ValueError("PDF vide")
                
                print("   📧 Import render_to_string...")
                from django.template.loader import render_to_string
                print("   ✅ Import OK")
                
                print("   📧 Préparation contexte...")
                context = {
                    'candidat': candidat,
                    'filiere': candidat.filiere
                }
                print("   ✅ Contexte OK")
                
                print("   📧 Rendu template...")
                html_message = render_to_string(
                    'emails/validation_enrollement.html',
                    context
                )
                print(f"   ✅ Template rendu: {len(html_message)} caractères")
                
                print("   📧 Import EmailMessage...")
                from django.core.mail import EmailMessage
                from django.conf import settings
                print("   ✅ Import OK")
                
                print("   📧 Création EmailMessage...")
                email = EmailMessage(
                    subject=f'✅ Validation de votre enrôlement - {candidat.filiere.libelle}',
                    body=html_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[candidat.email],
                )
                print("   ✅ Email créé")
                
                print("   📧 Définition content_subtype...")
                email.content_subtype = "html"
                print("   ✅ Content type défini")
                
                print("   📎 Attachement PDF...")
                filename = f'Fiche_Enrollement_{candidat.matricule}.pdf'
                email.attach(filename, pdf_buffer.getvalue(), 'application/pdf')
                print(f"   ✅ PDF attaché: {filename}")
                print(f"   📋 Pièces jointes: {len(email.attachments)}")
                
                print("   📤 Envoi email...")
                result = email.send(fail_silently=False)
                print(f"   ✅ Envoi terminé: result={result}")
                
                if result == 1:
                    print(f"   🎉 EMAIL ENVOYÉ à {candidat.email}")
                else:
                    print(f"   ⚠️ result={result} (attendu 1)")
                
            except Exception as email_error:
                print(f"\n❌ ERREUR DANS BLOC EMAIL:")
                print(f"   Type: {type(email_error).__name__}")
                print(f"   Message: {str(email_error)}")
                import traceback
                traceback.print_exc()
                print("   ⚠️ DOSSIER VALIDÉ mais email NON envoyé")
            
            print("6️⃣ Retour Response...")
            print("="*80 + "\n")
            
            return Response({
                'success': True,
                'message': 'Dossier validé avec succès',
                'candidat': {
                    'id': candidat.id,
                    'matricule': candidat.matricule,
                    'statut': candidat.statut_dossier
                }
            })
            
        except Candidat.DoesNotExist:
            print("❌ Candidat non trouvé")
            return Response(
                {'error': 'Candidat non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(f"❌ ERREUR GÉNÉRALE: {e}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='rejeter-dossier')
    def rejeter_dossier(self, request, pk=None):
        """Rejeter le dossier d'un candidat avec motif"""
        try:
            user = request.user
            rf_profile = user.responsable_filiere_profile
            motif = request.data.get('motif', '')
            
            if not motif:
                return Response(
                    {'error': 'Le motif de rejet est obligatoire'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            candidat = Candidat.objects.get(
                id=pk,
                filiere=rf_profile.filiere
            )
            
            # Rejeter le dossier
            candidat.statut_dossier = 'rejete'
            if hasattr(candidat, 'motif_rejet'):
                candidat.motif_rejet = motif
            if hasattr(candidat, 'date_rejet'):
                candidat.date_rejet = timezone.now()
            if hasattr(candidat, 'rejete_par'):
                candidat.rejete_par = user
            candidat.save()
            
            # Envoyer l'email
            try:
                context = {
                    'candidat': candidat,
                    'motif': motif,
                    'filiere': candidat.filiere
                }
                
                html_message = render_to_string(
                    'emails/rejet_enrollement.html',
                    context
                )
                
                email = EmailMessage(
                    subject=f'📋 Notification concernant votre dossier - {candidat.filiere.libelle}',
                    body='Votre dossier a été examiné. Veuillez consulter les détails ci-dessous.',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[candidat.email],
                )
                
                # Ajouter le HTML
                email.content_subtype = "html"
                email.body = html_message
                
                # Envoyer l'email
                email.send(fail_silently=False)
                
                print(f"✅ Email de rejet envoyé à {candidat.email}")
                
            except Exception as email_error:
                print(f"❌ Erreur envoi email: {email_error}")
                import traceback
                traceback.print_exc()
            
            return Response({
                'success': True,
                'message': 'Dossier rejeté avec succès',
                'candidat': {
                    'id': candidat.id,
                    'matricule': candidat.matricule,
                    'statut': candidat.statut_dossier,
                    'motif_rejet': motif
                }
            })
            
        except Candidat.DoesNotExist:
            return Response(
                {'error': 'Candidat non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
