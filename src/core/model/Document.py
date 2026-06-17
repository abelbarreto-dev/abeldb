from uuid import UUID

from pydantic import BaseModel


class Document(BaseModel):
    id_document: UUID
