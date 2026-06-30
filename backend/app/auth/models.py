from typing import Literal

from pydantic import BaseModel


class AuthenticatedPrincipal(BaseModel):
    subject: str
    role: Literal["admin"] = "admin"
