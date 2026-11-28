"""
Módulo de Upload Automático via YouTube Data API v3 com Governança Human-in-the-Loop.
Gerencia OAuth2, quota e agendamento de Shorts com trava de segurança estrita.
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("IAS.YouTubeUploader")

class YouTubeUploader:
    def __init__(self, credentials_dir: Optional[str] = None):
        base_dir = Path(__file__).resolve().parent.parent
        self.creds_dir = Path(credentials_dir) if credentials_dir else (base_dir / "credentials")
        self.creds_dir.mkdir(parents=True, exist_ok=True)

    def upload_short(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list = None,
        publish_time_iso: Optional[str] = None,
        channel_config: Optional[Dict[str, Any]] = None,
        human_approved: bool = False,
        human_approval_token: Optional[str] = None,
        privacy_status: str = "private"
    ) -> Dict[str, Any]:
        """
        Faz o upload oficial do vídeo curto (Shorts) para o canal especificado.
        REGRA MANDATÓRIA: Exige aprovação humana expressa e força 'private' por padrão.
        """
        # 1. Trava de Governança Human-in-the-Loop
        if not human_approved or not human_approval_token:
            msg = "[YouTubeUploader] BLOQUEIO DE SEGURANÇA: Upload não autorizado. Aprovação humana mandatória pendente."
            logger.warning(msg)
            return {
                "status": "BLOCKED_AWAITING_APPROVAL",
                "error": msg,
                "path": str(video_path),
                "title": title
            }

        # 2. Blindagem de Privacidade: força 'private' como padrão inalterável para proteção operacional
        safe_privacy = "private" if privacy_status != "unlisted" else "unlisted"

        print(f"[YouTubeUploader] Enviando '{title}' para o YouTube (Status: {safe_privacy})...")
        try:
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
            from google.oauth2.credentials import Credentials

            tags = tags or ["shorts", "podcast", "cortes"]
            
            # Se existirem credenciais OAuth válidas configuradas
            if channel_config and "refresh_token" in channel_config and channel_config["refresh_token"] != "SEU_REFRESH_TOKEN_1":
                creds = Credentials(
                    token=None,
                    refresh_token=channel_config["refresh_token"],
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=channel_config.get("client_id"),
                    client_secret=channel_config.get("client_secret")
                )
                youtube = build("youtube", "v3", credentials=creds)

                body = {
                    "snippet": {
                        "title": title[:100],
                        "description": description,
                        "tags": tags,
                        "categoryId": "22"  # People & Blogs
                    },
                    "status": {
                        "privacyStatus": safe_privacy,
                        "selfDeclaredMadeForKids": False
                    }
                }
                if publish_time_iso:
                    body["status"]["publishAt"] = publish_time_iso

                media = MediaFileUpload(
                    str(video_path),
                    mimetype="video/mp4",
                    resumable=True,
                    chunksize=1024*1024*5
                )

                request = youtube.videos().insert(
                    part="snippet,status",
                    body=body,
                    media_body=media
                )
                response = None
                while response is None:
                    status, response = request.next_chunk()
                    if status:
                        print(f" -> Progresso upload YouTube: {int(status.progress() * 100)}%")

                video_id = response.get("id")
                print(f"[YouTubeUploader] Enviado com sucesso em modo seguro ({safe_privacy})! https://youtube.com/shorts/{video_id}")
                return {
                    "status": "SUCCESS",
                    "video_id": video_id,
                    "url": f"https://youtube.com/shorts/{video_id}",
                    "privacy": safe_privacy
                }

            else:
                print(f"[YouTubeUploader] Modo Simulação Auditada: Credenciais pendentes de conexão OAuth.")
                return {
                    "status": "SIMULATED",
                    "path": str(video_path),
                    "title": title,
                    "privacy": safe_privacy,
                    "approval_token": human_approval_token
                }

        except Exception as e:
            print(f"[YouTubeUploader] Erro no upload: {e}")
            return {"status": "ERROR", "error": str(e)}
