from typing import Optional, Dict
import httpx
from fastapi import HTTPException

from app.core.config import settings


async def get_google_token(code: str) -> Dict:
    """获取 Google OAuth token"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": settings.google_oauth.client_id,
                    "client_secret": settings.google_oauth.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.google_oauth.redirect_uri
                }
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to get Google token: {str(e)}"
            )


async def get_google_user_info(access_token: str) -> Dict:
    """获取 Google 用户信息"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to get Google user info: {str(e)}"
            ) 