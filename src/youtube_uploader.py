import os

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request


def _get_client():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/youtube"],
    )
    creds.refresh(Request())
    return build("youtube", "v3", credentials=creds)


def upload_video(video_path, content):
    youtube = _get_client()

    # YouTube rejeita "<" e ">" no título/descrição (invalidDescription)
    clean = lambda s: s.replace("<", "‹").replace(">", "›")
    title = clean(content["youtube_title"])[:100]
    description = clean(content.get("youtube_description", ""))[:4900]
    tags = content.get("tags", [])

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "28",  # Science & Technology
            "defaultLanguage": "pt",
            "defaultAudioLanguage": "pt",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True, chunksize=5 * 1024 * 1024)

    print(f"📤 Enviando para YouTube: {title}")
    request = youtube.videos().insert(part=",".join(body.keys()), body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"   Upload: {pct}%")

    video_id = response["id"]
    url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"✅ Publicado: {url}")

    # Thumbnail oficial (aparece na busca, no canal e em "Relacionados").
    # Pode falhar se o canal não for verificado — o vídeo já está no ar mesmo assim.
    cover = content.get("cover_path")
    if cover and os.path.exists(cover):
        try:
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(cover, mimetype="image/jpeg")).execute()
            print("🖼️  Thumbnail personalizada aplicada")
        except Exception as e:
            print(f"⚠️  Thumbnail não aplicada ({e}); fica a capa do 1º quadro.")
    return {"id": video_id, "url": url}
