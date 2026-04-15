from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.time import utc_now
from app.core.security import decode_access_token, hash_api_key
from app.models import Account, AccountApiKey


@dataclass(slots=True)
class ActorContext:
    account: Account
    actor_type: str
    actor_id: str


def get_current_actor(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> ActorContext:
    if x_api_key:
        key_hash = hash_api_key(x_api_key)
        api_key = (
            db.query(AccountApiKey)
            .join(Account)
            .filter(AccountApiKey.key_hash == key_hash, AccountApiKey.is_active.is_(True), Account.is_active.is_(True))
            .one_or_none()
        )
        if api_key is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid api key")
        api_key.last_used_at = utc_now()
        db.add(api_key)
        db.commit()
        db.refresh(api_key)
        return ActorContext(account=api_key.account, actor_type="agent", actor_id=f"api-key:{api_key.id}")

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_access_token(token)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid bearer token") from exc

    account_id = payload.get("account_id")
    if not isinstance(account_id, int):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid bearer token")

    account = db.get(Account, account_id)
    if account is None or not account.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="account not found")
    return ActorContext(account=account, actor_type="user", actor_id=f"user:{account.id}")
