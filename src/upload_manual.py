"""Publica um vídeo pronto (feito fora do bot) no canal Brasil Digital.

Os arquivos vêm de um release do GitHub (vídeo grande não cabe no repositório):
    video.mp4, thumb.jpg, meta.json
meta.json: {"title", "description", "tags": [...], "categoryId", "privacyStatus",
            "containsSyntheticMedia": true/false}

    python src/upload_manual.py pasta_com_os_arquivos
"""
import json
import os
import sys

from googleapiclient.http import MediaFileUpload

from youtube_uploader import _get_client


def main(pasta):
    meta = json.load(open(os.path.join(pasta, "meta.json"), encoding="utf-8"))
    clean = lambda s: s.replace("<", "‹").replace(">", "›")  # YouTube rejeita < e >
    body = {
        "snippet": {
            "title": clean(meta["title"])[:100],
            "description": clean(meta["description"])[:4900],
            "tags": meta.get("tags", []),
            "categoryId": str(meta.get("categoryId", "27")),
            "defaultLanguage": "pt-BR",
            "defaultAudioLanguage": "pt-BR",
        },
        "status": {
            "privacyStatus": meta.get("privacyStatus", "private"),
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": bool(meta.get("containsSyntheticMedia", False)),
        },
    }
    youtube = _get_client()
    media = MediaFileUpload(os.path.join(pasta, "video.mp4"), mimetype="video/mp4",
                            resumable=True, chunksize=8 * 1024 * 1024)
    print(f"📤 Enviando: {body['snippet']['title']}")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"   Upload: {int(status.progress() * 100)}%")
    video_id = response["id"]
    print(f"✅ Publicado: https://www.youtube.com/watch?v={video_id}")

    thumb = os.path.join(pasta, "thumb.jpg")
    if os.path.exists(thumb):
        try:
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumb, mimetype="image/jpeg")).execute()
            print("🖼️  Thumbnail aplicada")
        except Exception as e:
            print(f"⚠️  Thumbnail não aplicada: {e}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main(sys.argv[1])
