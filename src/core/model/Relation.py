from enum import Enum

from pydantic import BaseModel


class RelationType(Enum):
    ONE_TO_ONE="ONE_TO_ONE"
    ONE_TO_MANY="ONE_TO_MANY"
    MANY_TO_MANY="MANY_TO_MANY"


class Relation(BaseModel):
    table_one_id: str
    table_two_id: str
    relation: RelationType
