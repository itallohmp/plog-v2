from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.security import (
    autenticar_usuario,
    criar_token_acesso,
    hash_senha,
    verificar_admin,
    verificar_token_acesso,
    verificar_token_refresh,
)
from app.database.db import get_db
from app.models.user import User
from app.schemas.auth import (
    AdminUserCreate,
    LogoutResponse,
    MessageResponse,
    TokenResponse,
    UserListItem,
    UserLogin,
    UserMeResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserMeResponse)
async def obter_usuario_atual(usuario: User = Depends(verificar_token_acesso)):
    return usuario


@router.get("/usuarios", response_model=list[UserListItem])
async def listar_usuarios(
    session: Session = Depends(get_db),
    _: User = Depends(verificar_admin),
):
    return session.query(User).order_by(User.username).all()


@router.post(
    "/registrar",
    response_model=UserListItem,
    status_code=status.HTTP_201_CREATED,
)
async def registrar(
    payload: AdminUserCreate,
    session: Session = Depends(get_db),
    _: User = Depends(verificar_admin),
):
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
        admin=payload.admin,
        ativo=True,
    )

    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.patch("/usuarios/{user_id}/ativo", response_model=UserListItem)
async def alternar_status_usuario(
    user_id: int,
    session: Session = Depends(get_db),
    admin_atual: User = Depends(verificar_admin),
):
    if user_id == admin_atual.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível alterar o status da própria conta.",
        )

    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        )

    user.ativo = not user.ativo
    session.commit()
    session.refresh(user)
    return user


@router.delete("/usuarios/{user_id}", response_model=MessageResponse)
async def remover_usuario(
    user_id: int,
    session: Session = Depends(get_db),
    admin_atual: User = Depends(verificar_admin),
):
    if user_id == admin_atual.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível remover a própria conta.",
        )

    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        )

    session.delete(user)
    session.commit()
    return MessageResponse(message="Usuário removido com sucesso.")


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
        admin=usuario.admin,
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
        admin=usuario.admin,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(usuario: User = Depends(verificar_token_refresh)):
    access_token = criar_token_acesso(usuario.id)
    refresh_token = criar_token_acesso(usuario.id, timedelta(days=7), tipo="refresh")
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        admin=usuario.admin,
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(usuario: User = Depends(verificar_token_acesso)):
    return LogoutResponse(message="Logout realizado com sucesso.")
