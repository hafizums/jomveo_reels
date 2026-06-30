from typing import Literal

from pydantic import BaseModel


class AuthenticatedPrincipal(BaseModel):
    subject: str
    role: Literal["admin", "user"] = "admin"
    user_id: str | None = None
    email: str | None = None
