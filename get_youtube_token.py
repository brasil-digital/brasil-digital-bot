"""
Rode este script UMA VEZ para obter o YOUTUBE_REFRESH_TOKEN.
Precisa de YOUTUBE_CLIENT_ID e YOUTUBE_CLIENT_SECRET nas variáveis de ambiente.

1. Crie um projeto no Google Cloud Console
2. Ative a YouTube Data API v3
3. Crie credenciais OAuth 2.0 (tipo: Desktop app)
4. Defina as variáveis e rode: python get_youtube_token.py
"""

import os
from google_auth_oauthlib.flow import InstalledAppFlow

CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID") or input("Client ID: ").strip()
CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET") or input("Client Secret: ").strip()

client_config = {
    "installed": {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

flow = InstalledAppFlow.from_client_config(
    client_config,
    scopes=["https://www.googleapis.com/auth/youtube"],
)

creds = flow.run_local_server(port=0)

import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
print("\nTokens obtidos com sucesso!")
print(f"\nYOUTUBE_REFRESH_TOKEN={creds.refresh_token}")
print("\nCopie esse valor e salve como secret no GitHub!")
