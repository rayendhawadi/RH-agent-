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
            "d'intégration (documents à déposer, tâches à suivre) est disponible ici :\n"
            "{{ checklist_link }}\n\n"
            "Une question sur l'entreprise (congés, avantages, outils internes...) ? "
            "Un assistant est directement disponible sur cette même page pour y répondre.\n\n"
            "L'équipe Welyne"
        ),
        "onboarding_document_reminder": (
            "Bonjour {{ candidate_name }},\n\n"
            "Petit rappel : le document \"{{ task_label }}\" pour votre intégration "
            "(\"{{ job_title }}\") n'a pas encore été déposé sur le portail. "
            "Merci de le faire dès que possible.\n\nL'équipe Welyne"
        ),
        "onboarding_documents_complete": (
            "Bravo {{ candidate_name }} !\n\n"
            "Tous vos documents pour \"{{ job_title }}\" ont été validés. "
            "Il ne reste plus qu'à profiter de votre intégration.\n\n"
            "Une question sur l'entreprise (congés, avantages, outils internes, "
            "processus internes...) ? Posez-la directement à notre assistant, "
            "disponible ici :\n{{ checklist_link }}\n\n"
            "L'équipe Welyne"
        ),
        "onboarding_escalation": (
            "Tâche d'onboarding en attente depuis {{ days_open }} jours.\n\n"
            "Candidat : {{ candidate_name }} — Poste : \"{{ job_title }}\"\n"
            "Tâche : {{ task_label }}\n\n"
            "Une relance a déjà été envoyée au candidat ; une vérification manuelle "
            "est recommandée."
        ),
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
            "Your onboarding checklist (documents to submit, tasks to track) is here:\n"
            "{{ checklist_link }}\n\n"
            "Have a question about the company (leave policy, perks, internal tools...)? "
            "An assistant is available right on that same page to answer it.\n\n"
            "The Welyne team"
        ),
        "onboarding_document_reminder": (
            "Hi {{ candidate_name }},\n\n"
            "Quick reminder: the document \"{{ task_label }}\" for your onboarding "
            "(\"{{ job_title }}\") hasn't been uploaded yet. Please submit it on the "
            "portal as soon as you can.\n\nThe Welyne team"
        ),
        "onboarding_documents_complete": (
            "Great news {{ candidate_name }}!\n\n"
            "All your documents for \"{{ job_title }}\" have been validated. "
            "Now just enjoy settling in.\n\n"
            "Have a question about the company (leave policy, perks, internal "
            "tools, internal processes...)? Ask our assistant directly, "
            "available here:\n{{ checklist_link }}\n\n"
            "The Welyne team"
        ),
        "onboarding_escalation": (
            "Onboarding task pending for {{ days_open }} days.\n\n"
            "Candidate: {{ candidate_name }} — Role: \"{{ job_title }}\"\n"
            "Task: {{ task_label }}\n\n"
            "A reminder has already been sent to the candidate; a manual check is "
            "recommended."
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