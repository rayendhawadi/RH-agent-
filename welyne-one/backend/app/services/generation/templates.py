"""
Bibliothèque de templates (§5.2, A7). Rendu Jinja2 ; personnalisation LLM
uniquement dans des emplacements bornés (voir service.py, max 2 phrases).
Seuls les templates FR/EN "ack" et "decline" sont couverts pleinement en
phase 2 — les autres (offre, onboarding) seront complétés en phase 3-4.
"""
from jinja2 import Template

TEMPLATES: dict[str, dict[str, str]] = {
    "fr": {
        "ack": (
            "Bonjour {{ candidate_name }},\n\n"
            "Nous avons bien reçu votre candidature pour le poste \"{{ job_title }}\". "
            "Un assistant IA nous aide à traiter les candidatures ; une décision humaine "
            "sera prise à chaque étape clé. Nous revenons vers vous rapidement.\n\n"
            "Cordialement,\nL'équipe recrutement"
        ),
        "invite_prescreen": (
            "Bonjour {{ candidate_name }},\n\n"
            "Votre profil a retenu notre attention pour \"{{ job_title }}\". "
            "Nous vous invitons à répondre à quelques questions rapides via ce lien : "
            "{{ prescreen_link }}\n\nCordialement,\nL'équipe recrutement"
        ),
        "invite_interview": (
            "Bonjour {{ candidate_name }},\n\n"
            "Nous souhaitons vous rencontrer pour le poste \"{{ job_title }}\". "
            "Voici 3 créneaux proposés :\n{{ slot_options }}\n\n"
            "Choisissez-en un ici : {{ booking_link }}\n\n"
            "Cordialement,\nL'équipe recrutement"
        ),
        "interview_confirmed": (
            "Bonjour {{ candidate_name }},\n\n"
            "Votre entretien pour \"{{ job_title }}\" est confirmé : {{ slot_text }}. "
            "Une invitation calendrier (.ics) est jointe.\n\n"
            "Cordialement,\nL'équipe recrutement"
        ),
        "interview_reminder": (
            "Bonjour {{ candidate_name }},\n\n"
            "Petit rappel : votre entretien pour \"{{ job_title }}\" a lieu demain, {{ slot_text }}.\n\n"
            "Cordialement,\nL'équipe recrutement"
        ),
        "interview_rescheduled": (
            "Bonjour {{ candidate_name }},\n\n"
            "Votre entretien pour \"{{ job_title }}\" a été replanifié : {{ slot_text }}. {{ reason }}\n\n"
            "Cordialement,\nL'équipe recrutement"
        ),
        "interview_cancelled": (
            "Bonjour {{ candidate_name }},\n\n"
            "Votre entretien pour \"{{ job_title }}\" a été annulé. {{ reason }}\n"
            "Nous reviendrons vers vous si un nouveau créneau est proposé.\n\n"
            "Cordialement,\nL'équipe recrutement"
        ),
        "decline": (
            "Bonjour {{ candidate_name }},\n\n"
            "Après étude attentive de votre candidature pour \"{{ job_title }}\", "
            "nous ne donnerons pas suite pour le moment. {{ personalized_note }}\n"
            "Nous vous souhaitons une belle continuation.\n\n"
            "Cordialement,\nL'équipe recrutement"
        ),
        "offer": (
            "Bonjour {{ candidate_name }},\n\n"
            "Nous avons le plaisir de vous proposer le poste \"{{ job_title }}\". "
            "Détails en pièce jointe / à suivre.\n\nCordialement,\nL'équipe recrutement"
        ),
        "onboarding_welcome": (
            "Bienvenue {{ candidate_name }} !\n\n"
            "Ravis de vous accueillir pour \"{{ job_title }}\". Votre checklist "
            "d'intégration est disponible ici : {{ checklist_link }}\n\nL'équipe Welyne"
        ),
        "onboarding_reminder": (
            "Bonjour {{ candidate_name }},\n\n"
            "Petit rappel pour votre intégration \"{{ job_title }}\" : il reste à "
            "faire : {{ missing_tasks }}. Merci de compléter dès que possible.\n\n"
            "L'équipe Welyne"
        ),
        "onboarding_escalation": (
            "Tâche d'onboarding en retard pour {{ candidate_name }} (\"{{ job_title }}\") : "
            "{{ task }}. Aucune action depuis plus de 5 jours après relance."
        ),
        # A5 (§6-A5) — chaque tour du dialogue de pré-qualification (email/
        # whatsapp). Pas de formule de politesse ajoutée ici : le texte est
        # déjà entièrement rédigé par l'agent A5 (consentement, question,
        # relance, etc.), ce template ne fait que le faire passer par le
        # point de passage unique A7 (journalisation message_log).
        "prescreen_message": "{{ body }}",
    },
    "en": {
        "ack": (
            "Hello {{ candidate_name }},\n\n"
            "We received your application for \"{{ job_title }}\". An AI assistant "
            "helps us process applications; a human makes every key decision. "
            "We'll get back to you shortly.\n\nBest regards,\nThe recruiting team"
        ),
        "invite_prescreen": (
            "Hello {{ candidate_name }},\n\nYour profile stood out for \"{{ job_title }}\". "
            "Please answer a few quick questions here: {{ prescreen_link }}\n\n"
            "Best regards,\nThe recruiting team"
        ),
        "invite_interview": (
            "Hello {{ candidate_name }},\n\nWe'd like to meet you for \"{{ job_title }}\". "
            "Here are 3 proposed slots:\n{{ slot_options }}\n\n"
            "Pick one here: {{ booking_link }}\n\nBest regards,\nThe recruiting team"
        ),
        "interview_confirmed": (
            "Hello {{ candidate_name }},\n\nYour interview for \"{{ job_title }}\" is confirmed: "
            "{{ slot_text }}. A calendar invite (.ics) is attached.\n\nBest regards,\nThe recruiting team"
        ),
        "interview_reminder": (
            "Hello {{ candidate_name }},\n\nQuick reminder: your interview for \"{{ job_title }}\" "
            "is tomorrow, {{ slot_text }}.\n\nBest regards,\nThe recruiting team"
        ),
        "interview_rescheduled": (
            "Hello {{ candidate_name }},\n\nYour interview for \"{{ job_title }}\" has been rescheduled: "
            "{{ slot_text }}. {{ reason }}\n\nBest regards,\nThe recruiting team"
        ),
        "interview_cancelled": (
            "Hello {{ candidate_name }},\n\nYour interview for \"{{ job_title }}\" has been cancelled. "
            "{{ reason }}\nWe'll be in touch if a new slot is proposed.\n\nBest regards,\nThe recruiting team"
        ),
        "decline": (
            "Hello {{ candidate_name }},\n\n"
            "After careful review of your application for \"{{ job_title }}\", "
            "we won't move forward at this time. {{ personalized_note }}\n"
            "We wish you all the best.\n\nBest regards,\nThe recruiting team"
        ),
        "offer": (
            "Hello {{ candidate_name }},\n\nWe're pleased to offer you \"{{ job_title }}\". "
            "Details attached / to follow.\n\nBest regards,\nThe recruiting team"
        ),
        "onboarding_welcome": (
            "Welcome {{ candidate_name }}!\n\nExcited to have you for \"{{ job_title }}\". "
            "Your onboarding checklist is here: {{ checklist_link }}\n\nThe Welyne team"
        ),
        "onboarding_reminder": (
            "Hi {{ candidate_name }},\n\nQuick reminder for your onboarding (\"{{ job_title }}\"): "
            "still pending: {{ missing_tasks }}. Please complete as soon as you can.\n\n"
            "The Welyne team"
        ),
        "onboarding_escalation": (
            "Overdue onboarding task for {{ candidate_name }} (\"{{ job_title }}\"): "
            "{{ task }}. No action for more than 5 days after the reminder."
        ),
        "prescreen_message": "{{ body }}",
    },
}


def render_template(template_id: str, language: str, context: dict) -> str:
    lang = language if language in TEMPLATES else "fr"
    raw = TEMPLATES[lang].get(template_id)
    if raw is None:
        raise ValueError(f"Template inconnu : {template_id}")
    return Template(raw).render(**context)