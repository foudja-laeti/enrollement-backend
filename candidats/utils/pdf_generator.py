# candidats/utils/pdf_generator.py
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas
from io import BytesIO
import qrcode
from django.conf import settings
import os

def generer_fiche_enrollement(candidat):
    """
    Génère la fiche d'enrôlement PDF professionnelle
    """
    buffer = BytesIO()
    
    # Créer le document PDF
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Style personnalisé pour le titre
    style_titre = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    style_section = ParagraphStyle(
        'Section',
        parent=styles['Heading2'],
        fontSize=11,
        textColor=colors.white,
        spaceAfter=10,
        alignment=TA_LEFT,
        fontName='Helvetica-Bold',
        backColor=colors.HexColor('#4F46E5'),
        leftIndent=10,
        rightIndent=10,
        spaceBefore=10,
    )
    
    style_normal = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#374151'),
        fontName='Helvetica'
    )
    
    # Contenu du document
    story = []
    
    # === EN-TÊTE ===
    header_data = [
        [
            Paragraph("<b>RÉPUBLIQUE DU CAMEROUN</b><br/>Paix - Travail - Patrie<br/><br/>"
                     "UNIVERSITÉ D'EBOLOWA<br/><br/>"
                     "ÉCOLE SUPÉRIEURE DE TRANSPORT,<br/>DE LOGISTIQUE ET DE COMMERCE", 
                     ParagraphStyle('header_left', parent=style_normal, fontSize=8, alignment=TA_CENTER)),
            # Logo au centre (si disponible)
            Paragraph("", style_normal),
            Paragraph("<b>REPUBLIC OF CAMEROON</b><br/>Peace - Work - Fatherland<br/><br/>"
                     "THE UNIVERSITY OF EBOLOWA<br/><br/>"
                     "HIGHER INSTITUTE OF TRANSPORT,<br/>LOGISTICS AND COMMERCE",
                     ParagraphStyle('header_right', parent=style_normal, fontSize=8, alignment=TA_CENTER))
        ]
    ]
    
    header_table = Table(header_data, colWidths=[7*cm, 4*cm, 7*cm])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOX', (0, 0), (-1, -1), 2, colors.black),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.5*cm))
    
    # === TITRE ===
    story.append(Paragraph(
        "FICHE D'INSCRIPTION AU CONCOURS D'ENTRÉE À L'ESTLC SESSION 2025",
        style_titre
    ))
    story.append(Paragraph(
        f"<b>CURSUS {candidat.filiere.libelle.upper()}</b>",
        ParagraphStyle('cursus', parent=style_titre, fontSize=12, textColor=colors.HexColor('#DC2626'))
    ))
    story.append(Spacer(1, 0.3*cm))
    
    # === MATRICULE ===
    matricule_data = [[
        Paragraph(f"<b>INSCRIPTION N° {candidat.matricule}</b>", 
                 ParagraphStyle('mat', parent=style_normal, fontSize=11, alignment=TA_CENTER)),
        Paragraph("Timbre Fiscal ici /<br/>Stamp here", 
                 ParagraphStyle('stamp', parent=style_normal, fontSize=8, alignment=TA_CENTER))
    ]]
    matricule_table = Table(matricule_data, colWidths=[14*cm, 4*cm])
    matricule_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(matricule_table)
    story.append(Spacer(1, 0.5*cm))
    
    # === PHOTO ET QR CODE ===
    photo_qr_data = []
    
    # Générer le QR Code
    qr_data = f"MATRICULE:{candidat.matricule}|NOM:{candidat.nom}|PRENOM:{candidat.prenom}|FILIERE:{candidat.filiere.code}"
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)
    qr_image = Image(qr_buffer, width=3*cm, height=3*cm)
    
    # Photo du candidat
    photo_placeholder = Paragraph("Photo<br/>3.5x4cm", 
                                 ParagraphStyle('photo', parent=style_normal, alignment=TA_CENTER))
    
    photo_qr_data = [[photo_placeholder, "", qr_image]]
    photo_qr_table = Table(photo_qr_data, colWidths=[3.5*cm, 11*cm, 3.5*cm])
    photo_qr_table.setStyle(TableStyle([
        ('BOX', (0, 0), (0, 0), 1, colors.black),
        ('BOX', (2, 0), (2, 0), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    story.append(photo_qr_table)
    story.append(Spacer(1, 0.5*cm))
    
    # === INFORMATIONS PERSONNELLES ===
    story.append(Paragraph("Informations Personnelles / Personal Informations", style_section))
    
    info_perso_data = [
        ["Nom:", Paragraph(f"<b>{candidat.nom}</b>", style_normal), 
         "Prénom:", Paragraph(f"<b>{candidat.prenom}</b>", style_normal)],
        ["Date naissance:", candidat.date_naissance.strftime('%Y-%m-%d') if candidat.date_naissance else "N/A",
         "Lieu de naissance:", candidat.lieu_naissance or "N/A",
         "Sexe:", "Masculin" if candidat.sexe == 'M' else "Féminin"],
        ["Nationalité:", "Cameroun",
         "Région d'origine:", candidat.region.nom if candidat.region else "N/A",
         "Département:", candidat.departement.nom if candidat.departement else "N/A"],
        ["CNI:", "N/A", "Téléphone:", candidat.telephone or "N/A", "Adresse:", candidat.ville or "N/A"],
        ["1ère Langue:", "Français", "Email:", candidat.email, "", ""],
    ]
    
    info_perso_table = Table(info_perso_data, colWidths=[3*cm, 5*cm, 3*cm, 5*cm, 2*cm, 4*cm])
    info_perso_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(info_perso_table)
    story.append(Spacer(1, 0.3*cm))
    
    # === INFORMATIONS ACADÉMIQUES ===
    story.append(Paragraph("Informations Académiques / Academic Informations", style_section))
    
    info_acad_data = [
        ["Diplôme d'admission:", "Licence Académique", "", ""],
        ["Filière:", candidat.filiere.code if candidat.filiere else "N/A",
         candidat.filiere.libelle.upper() if candidat.filiere else "N/A",
         "Mention:", candidat.mention.libelle if candidat.mention else "PASSABLE"],
        ["Année diplôme:", str(candidat.annee_obtention_diplome) if candidat.annee_obtention_diplome else "N/A",
         "Centre d'examen:", candidat.centre_examen.nom if candidat.centre_examen else "N/A",
         "Centre de dépôt:", candidat.centre_depot.nom if candidat.centre_depot else "N/A"],
    ]
    
    info_acad_table = Table(info_acad_data, colWidths=[4*cm, 4*cm, 6*cm, 4*cm])
    info_acad_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#F3F4F6')),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(info_acad_table)
    story.append(Spacer(1, 0.3*cm))
    
    # === AUTRES INFORMATIONS ===
    story.append(Paragraph("Autres Informations / Other Informations", style_section))
    
    autres_info_data = [
        ["Nom du père:", candidat.nom_pere or "N/A", "Téléphone du père:", candidat.tel_pere or "N/A"],
        ["Nom de la mère:", candidat.nom_mere or "N/A", "Téléphone de la mère:", candidat.tel_mere or "N/A"],
    ]
    
    autres_table = Table(autres_info_data, colWidths=[4*cm, 6*cm, 4*cm, 4*cm])
    autres_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(autres_table)
    story.append(Spacer(1, 0.5*cm))
    
    # === DOCUMENTS NÉCESSAIRES ===
    story.append(Paragraph("<b>Documents Nécessaires / Necessary Documents</b>", 
                          ParagraphStyle('doc_title', parent=style_normal, fontSize=10, textColor=colors.HexColor('#DC2626'))))
    story.append(Spacer(1, 0.2*cm))
    
    documents_text = """
    - Une photocopie certifiée d'acte de naissance datant de moins de trois (3) mois
    - Un extrait de casier judiciaire datant de moins de trois (3) mois
    - Un certificat médical délivré par un médecin fonctionnaire
    - Quatre (04) photos d'identité 4x4 du candidat
    - Un reçu de quitus d'un montant de 20 000F pour les 1ère années et de 25 000F pour les 3ème années
    - Une enveloppe A4 timbrée au tarif règlementaire et portant l'adresse exacte du candidat
    """
    
    story.append(Paragraph(documents_text, ParagraphStyle('docs', parent=style_normal, fontSize=8, leftIndent=20)))
    story.append(Spacer(1, 0.5*cm))
    
    # === PIED DE PAGE ===
    footer_data = [[
        Paragraph(f"<b>Code Candidat: {candidat.id}</b>", style_normal),
        Paragraph(f"<b>Imprimée le {candidat.date_validation.strftime('%d/%m/%Y') if hasattr(candidat, 'date_validation') and candidat.date_validation else 'N/A'}</b>", 
                 ParagraphStyle('footer_right', parent=style_normal, alignment=TA_CENTER))
    ]]
    
    footer_table = Table(footer_data, colWidths=[9*cm, 9*cm])
    footer_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    story.append(footer_table)
    
    # Construire le PDF
    doc.build(story)
    
    # CRITIQUE: Réinitialiser le pointeur à 0
    buffer.seek(0)
    
    return buffer