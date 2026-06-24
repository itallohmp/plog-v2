from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.core.config import (
    API_PREFIX,
    FLOW_ACCESS_TOKEN_EXPIRE_MINUTES,
    FLOW_ALGORITHM,
    FLOW_PLOG_SECRET_KEY,
)
from app.database.db import get_db
from app.models.user import User

password_hash = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{API_PREFIX}/auth/login-form")

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=401,
    detail="Token inválido",
    headers={"WWW-Authenticate": "Bearer"},
)


def verificar_senha(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def hash_senha(password: str) -> str:
    return password_hash.hash(password)


def autenticar_usuario(username: str, senha: str, session: Session) -> User | None:
    usuario = session.query(User).filter(User.username == username).first()
    if not usuario or not usuario.ativo:
        return None
    if not verificar_senha(senha, usuario.senha):
        return None
    return usuario


def criar_token_acesso(
    usuario_id: int,
    duracao_token=timedelta(minutes=FLOW_ACCESS_TOKEN_EXPIRE_MINUTES),
    tipo: str = "access",
) -> str:
    data_exp = datetime.now(timezone.utc) + duracao_token
    dic_info = {"sub": str(usuario_id), "exp": data_exp, "type": tipo}
    jwt_token = jwt.encode(dic_info, FLOW_PLOG_SECRET_KEY, algorithm=FLOW_ALGORITHM)
    return jwt_token


def _obter_usuario_do_token(token: str, session: Session, tipo_esperado: str) -> User:
    try:
        dict_info = jwt.decode(token, FLOW_PLOG_SECRET_KEY, algorithms=[FLOW_ALGORITHM])
        id_usuario = int(dict_info.get("sub"))
        if dict_info.get("type") != tipo_esperado:
            raise _CREDENTIALS_EXCEPTION
    except (JWTError, TypeError, ValueError):
        raise _CREDENTIALS_EXCEPTION from None

    usuario = session.query(User).filter(User.id == id_usuario).first()
    if not usuario or not usuario.ativo:
        raise HTTPException(
            status_code=401,
            detail="Acesso inválido ou usuário inativo",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return usuario


def verificar_token_acesso(
    token: str = Depends(oauth2_scheme), session: Session = Depends(get_db)
):
    return _obter_usuario_do_token(token, session, "access")


def verificar_token_refresh(
    token: str = Depends(oauth2_scheme), session: Session = Depends(get_db)
):
    return _obter_usuario_do_token(token, session, "refresh")


def verificar_admin(usuario: User = Depends(verificar_token_acesso)) -> User:
    if not usuario.admin:
        raise HTTPException(
            status_code=403,
            detail="Acesso restrito a administradores.",
        )
    return usuario
