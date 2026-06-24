from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.security import (
    autenticar_usuario,
    criar_token_acesso,
    hash_senha,
    verificar_token_acesso,
    verificar_token_refresh,
)
from app.database.db import get_db
from app.models.user import User
from app.schemas.auth import (
    LogoutResponse,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/registrar", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def registrar(payload: UserCreate, session: Session = Depends(get_db)):
    if session.query(User).filter(User.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Usuário já cadastrado neste email.",
        )

    if session.query(User).filter(User.username == payload.username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Login já existe.",
        )

    user = User(
        email=payload.email,
        username=payload.username,
        senha=hash_senha(payload.senha),
    )

    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, session: Session = Depends(get_db)):
    usuario = autenticar_usuario(payload.username, payload.senha, session)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos.",
        )

    access_token = criar_token_acesso(usuario.id)
    refresh_token = criar_token_acesso(usuario.id, timedelta(days=7), tipo="refresh")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/login-form", response_model=TokenResponse)
async def login_form(
    dados_formulario: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_db),
):

    usuario = autenticar_usuario(
        dados_formulario.username, dados_formulario.password, session
    )

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos.",
        )

    access_token = criar_token_acesso(usuario.id)
    refresh_token = criar_token_acesso(usuario.id, timedelta(days=7), tipo="refresh")
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(usuario: User = Depends(verificar_token_refresh)):
    access_token = criar_token_acesso(usuario.id)
    refresh_token = criar_token_acesso(usuario.id, timedelta(days=7), tipo="refresh")
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(usuario: User = Depends(verificar_token_acesso)):
    return LogoutResponse(message="Logout realizado com sucesso.")
