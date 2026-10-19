import secrets
from datetime import datetime, timedelta
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.auth import (
    create_access_token, create_signed_token, decode_signed_token, decrypt_secret,
    encrypt_secret, hash_password, new_opaque_token, new_totp_secret,
    token_digest, verify_and_upgrade_password, verify_totp,
)
from app.database import get_db
from app.mailer import is_configured, send_password_reset, send_verification

router = APIRouter(prefix="/auth", tags=["Autenticação"])
GENERIC_RESEND = {"message": "Se o cadastro existir, enviaremos um link de confirmação para o e-mail informado."}


def rate_limit(db: Session, namespace: str, value: str, limit: int, minutes: int = 15) -> None:
    digest = token_digest(f"{namespace}:{value}")
    now = datetime.utcnow()
    row = db.query(models.AuthThrottle).filter_by(key_hash=digest).with_for_update().first()
    if not row:
        row = models.AuthThrottle(key_hash=digest, attempts=0, window_started_at=now)
        db.add(row)
        db.flush()
    if row.window_started_at < now - timedelta(minutes=minutes):
        row.attempts, row.window_started_at = 0, now
    if row.attempts >= limit:
        raise HTTPException(status_code=429, detail="Muitas tentativas. Aguarde e tente novamente.", headers={"Retry-After": "900"})
    row.attempts += 1
    db.commit()


def issue_email_verification(db: Session, user: models.User) -> None:
    raw = new_opaque_token()
    row = db.query(models.EmailVerification).filter_by(user_id=user.id).first()
    if row:
        row.token_hash = token_digest(raw)
        row.expires_at = datetime.utcnow() + timedelta(minutes=30)
    else:
        db.add(models.EmailVerification(user_id=user.id, token_hash=token_digest(raw), expires_at=datetime.utcnow() + timedelta(minutes=30)))
    db.commit()
    send_verification(user.email, raw)


def issue_login_challenge(db: Session, user_id: int) -> str:
    raw = new_opaque_token()
    db.add(models.LoginChallenge(token_hash=token_digest(raw), user_id=user_id, expires_at=datetime.utcnow() + timedelta(minutes=5)))
    db.commit()
    return raw


def verified_user(db: Session, token: str, expected_type: str):
    try:
        payload = decode_signed_token(token)
        if payload.get("type") != expected_type:
            raise ValueError
        user_id = int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    user = db.query(models.User).filter_by(id=user_id).first()
    if not user or not db.query(models.VerifiedEmail).filter_by(user_id=user_id).first():
        raise HTTPException(status_code=403, detail="Confirme seu e-mail para continuar.")
    return user


@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    email = user.email.strip().lower()
    rate_limit(db, "register", email, 5, 60)
    if crud.get_user_by_email(db, email):
        raise HTTPException(status_code=409, detail="Este e-mail já possui uma conta. Entre ou solicite confirmação de e-mail.")
    try:
        result = crud.create_user(db, user.model_copy(update={"email": email}))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Este e-mail já possui uma conta.")
    # If delivery fails the account remains pending and can request another link later.
    issue_email_verification(db, result)
    return result


@router.post("/email/resend")
def resend_verification(payload: schemas.EmailInput, db: Session = Depends(get_db)):
    email = str(payload.email)
    rate_limit(db, "resend", email, 3, 60)
    user = crud.get_user_by_email(db, email)
    if user and not db.query(models.VerifiedEmail).filter_by(user_id=user.id).first():
        try:
            issue_email_verification(db, user)
        except HTTPException:
            pass
    return GENERIC_RESEND


@router.post("/email/verify")
def verify_email(payload: schemas.TokenInput, db: Session = Depends(get_db)):
    row = db.query(models.EmailVerification).filter_by(token_hash=token_digest(payload.token)).with_for_update().first()
    if not row or row.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Link inválido ou expirado. Solicite um novo e-mail de confirmação.")
    db.add(models.VerifiedEmail(user_id=row.user_id))
    db.delete(row)
    db.commit()
    return {"message": "E-mail confirmado. Entre para configurar seu segundo fator."}


@router.post("/password/forgot")
def forgot_password(payload: schemas.EmailInput, db: Session = Depends(get_db)):
    email = str(payload.email)
    rate_limit(db, "password-reset", email, 3, 60)
    if not is_configured():
        raise HTTPException(status_code=503, detail="O envio de e-mail ainda não está configurado.")
    user = crud.get_user_by_email(db, email)
    if user:
        raw = new_opaque_token()
        row = db.query(models.PasswordResetToken).filter_by(user_id=user.id).first()
        if row:
            row.token_hash = token_digest(raw)
            row.expires_at = datetime.utcnow() + timedelta(minutes=30)
        else:
            db.add(models.PasswordResetToken(user_id=user.id, token_hash=token_digest(raw), expires_at=datetime.utcnow() + timedelta(minutes=30)))
        db.commit()
        try:
            send_password_reset(user.email, raw)
        except HTTPException:
            # Keep the response identical for known and unknown addresses.
            pass
    return {"message": "Se o e-mail estiver cadastrado, enviaremos um link para redefinir a senha."}


@router.post("/password/reset")
def reset_password(payload: schemas.PasswordResetInput, db: Session = Depends(get_db)):
    row = db.query(models.PasswordResetToken).filter_by(token_hash=token_digest(payload.token)).with_for_update().first()
    if not row or row.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Link inválido ou expirado. Solicite uma nova redefinição de senha.")
    user_id = row.user_id
    user = db.query(models.User).filter_by(id=user_id).first()
    if not user:
        db.delete(row)
        db.commit()
        raise HTTPException(status_code=400, detail="Link inválido ou expirado.")
    user.hashed_password = hash_password(payload.new_password)
    db.query(models.PasswordResetToken).filter_by(user_id=user_id).delete(synchronize_session=False)
    db.query(models.LoginChallenge).filter_by(user_id=user_id).delete(synchronize_session=False)
    if not db.query(models.VerifiedEmail).filter_by(user_id=user_id).first():
        db.add(models.VerifiedEmail(user_id=user_id))
    db.commit()
    return {"message": "Senha redefinida. Entre com sua nova senha e confirme o segundo fator."}


@router.post("/login", response_model=schemas.LoginResult)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    email = form_data.username.strip().lower()
    rate_limit(db, "login", email, 10)
    user = crud.get_user_by_email(db, email)
    valid = False
    replacement = None
    if user:
        valid, replacement = verify_and_upgrade_password(form_data.password, user.hashed_password)
        if valid and replacement:
            user.hashed_password = replacement
            db.commit()
    if not user or not valid:
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")
    if not db.query(models.VerifiedEmail).filter_by(user_id=user.id).first():
        raise HTTPException(status_code=403, detail="Confirme seu e-mail antes de entrar. Use ‘Reenviar confirmação’ para receber outro link.")
    factor = db.query(models.Authenticator).filter_by(user_id=user.id).first()
    if factor and factor.enabled:
        return {"requires_mfa": True, "challenge_token": issue_login_challenge(db, user.id)}
    return {"requires_mfa_setup": True, "setup_token": create_signed_token({"sub": str(user.id), "type": "mfa_setup"}, 10)}


@router.post("/mfa/setup")
def setup_mfa(payload: schemas.TokenInput, db: Session = Depends(get_db)):
    user = verified_user(db, payload.token, "mfa_setup")
    factor = db.query(models.Authenticator).filter_by(user_id=user.id).first()
    if factor and factor.enabled:
        raise HTTPException(status_code=409, detail="O segundo fator já está configurado.")
    secret = new_totp_secret()
    if factor:
        factor.encrypted_secret = encrypt_secret(secret)
    else:
        db.add(models.Authenticator(user_id=user.id, encrypted_secret=encrypt_secret(secret), enabled=False))
    db.commit()
    label = quote(f"TaskFlow:{user.email}")
    uri = f"otpauth://totp/{label}?secret={secret}&issuer=TaskFlow&algorithm=SHA1&digits=6&period=30"
    return {"secret": secret, "otpauth_uri": uri, "instructions": "Adicione esta chave no Google Authenticator, Microsoft Authenticator ou 1Password. Depois confirme com o código de 6 dígitos."}


def create_recovery_codes(db: Session, user_id: int) -> list[str]:
    codes = [secrets.token_hex(5).upper() for _ in range(8)]
    for code in codes:
        db.add(models.RecoveryCode(user_id=user_id, code_hash=token_digest(code)))
    return codes


@router.post("/mfa/enable", response_model=schemas.LoginResult)
def enable_mfa(payload: schemas.MfaCodeInput, db: Session = Depends(get_db)):
    user = verified_user(db, payload.token, "mfa_setup")
    factor = db.query(models.Authenticator).filter_by(user_id=user.id).first()
    if not factor or factor.enabled or not verify_totp(decrypt_secret(factor.encrypted_secret), payload.code.strip()):
        raise HTTPException(status_code=400, detail="Código inválido. Confira o relógio do dispositivo e tente novamente.")
    factor.enabled = True
    codes = create_recovery_codes(db, user.id)
    db.commit()
    return {"access_token": create_access_token({"sub": str(user.id)}), "recovery_codes": codes}


@router.post("/mfa/verify", response_model=schemas.LoginResult)
def verify_mfa(payload: schemas.MfaCodeInput, db: Session = Depends(get_db)):
    challenge_hash = token_digest(payload.token)
    challenge = db.query(models.LoginChallenge).filter_by(token_hash=challenge_hash).with_for_update().first()
    if not challenge or challenge.consumed_at or challenge.expires_at < datetime.utcnow() or challenge.attempts >= 5:
        raise HTTPException(status_code=401, detail="Desafio inválido ou expirado. Entre novamente.")
    factor = db.query(models.Authenticator).filter_by(user_id=challenge.user_id, enabled=True).first()
    normalized = payload.code.strip().upper()
    valid = bool(factor and verify_totp(decrypt_secret(factor.encrypted_secret), normalized))
    recovery = None
    if not valid and factor:
        recovery = db.query(models.RecoveryCode).filter_by(user_id=challenge.user_id, code_hash=token_digest(normalized), used_at=None).first()
        valid = recovery is not None
    if not valid:
        challenge.attempts += 1
        db.commit()
        raise HTTPException(status_code=401, detail="Código inválido")
    if recovery:
        db.delete(recovery)
    challenge.consumed_at = datetime.utcnow()
    db.commit()
    return {"access_token": create_access_token({"sub": str(challenge.user_id)})}
