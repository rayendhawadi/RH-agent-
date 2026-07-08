"""Sortie de l'agent A1 — variantes de contenu par canal (§6, agent A1)."""
from pydantic import BaseModel


class ChannelContent(BaseModel):
    linkedin_post: str = ""
    job_board_text: str = ""
    careers_page_text: str = ""
    whatsapp_message: str = ""