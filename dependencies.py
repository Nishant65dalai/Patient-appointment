import sqlite3
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from auth import bearer_scheme, decode_token
from db import get_db


async def verify_jwt(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Protects a route with Depends(verify_jwt).

    Two different ways a request can fail here, both -> 401:

      1. INVALID token - missing, malformed, wrong signature, or
         expired. decode_token() raises for all four; jose doesn't
         hand us a clean way to tell them apart, and the fix is the
         same either way: log in again. This is the "invalid JWT"
         branch.
      2. VALID token, unknown user - signature checks out, it
         hasn't expired, but no row in `users` matches the username
         inside it (e.g. the account was deleted after the token was
         issued).

    Only when BOTH checks pass do you reach the final return: the DB
    row for the now-confirmed-real, currently-logged-in user. Every
    route using Depends(verify_jwt) gets this dict as the parameter.
    """
    payload = decode_token(creds.credentials)

    username: Optional[str] = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
        )

    row = db.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return dict(row)


async def require_admin(user: dict = Depends(verify_jwt)) -> dict:
    """Stacks on verify_jwt - everything above still runs first, so
    a bad token still dies as a 401 before this function's own check
    ever sees it.

    The one extra check: user["role"] == "admin".

    403, not 401: the token is fine and we know exactly who this is -
    they're just not allowed to do this. 401 means "we don't know who
    you are"; 403 means "we know, and the answer is no."
    """
    if user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required for this operation",
        )
    return user
