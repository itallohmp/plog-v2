import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(sa.String, unique=True, index=True)
    email: Mapped[str] = mapped_column(sa.String, unique=True, index=True)
    senha: Mapped[str] = mapped_column(sa.String)
    admin: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    ativo: Mapped[bool] = mapped_column(sa.Boolean, default=True)

    def __init__(self, username, email, senha, admin=False, ativo=True):
        self.username = username
        self.email = email
        self.senha = senha
        self.admin = admin
        self.ativo = ativo
