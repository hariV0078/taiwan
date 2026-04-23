import uuid
from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel


class UserRole(str, Enum):
    manufacturer = "manufacturer"
    buyer = "buyer"
    tpqc = "tpqc"
    admin = "admin"


class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    email: str = Field(unique=True, index=True)
    password_hash: str
    role: UserRole
    company: str
    country: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
