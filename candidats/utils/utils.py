# candidats/utils.py
from ..models import Notification

def create_notification(candidat, titre, message, type='info', action_url=None, action_label=None):
    """
    Créer une notification pour un candidat
    
    Args:
        candidat: Instance de Candidat
        titre: Titre de la notification
        message: Message détaillé
        type: Type de notification (success, validation, error, rejection, warning, info)
        action_url: URL optionnelle pour action
        action_label: Label du bouton d'action
    """
    return Notification.objects.create(
        candidat=candidat,
        titre=titre,
        message=message,
        type=type,
        action_url=action_url,
        action_label=action_label
    )