"""Séries do Shorts: cada tema do canal vira uma playlist só de Shorts.

A API do YouTube não cria "séries", mas toda série nasce de uma playlist.
O bot mantém uma playlist por série e adiciona cada Short publicado nela;
a conversão em série é feita uma vez à mão no YouTube Studio
(Conteúdo → Playlists → Opções → "Adicionar recursos de série").

Série de cada Short: campo "series" do roteiro (manuais), senão pela categoria.
Vídeos longos NÃO entram (série de Shorts aceita só Shorts).

Preencher com os Shorts já publicados (classifica pelo título):
    python src/series.py --backfill            # só mostra o plano
    python src/series.py --backfill --apply    # insere de verdade
"""
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

SERIES = {
    "real-ou-ia": {
        "title": "É Real ou É IA?",
        "description": "Vídeos virais analisados: é real ou foi feito por inteligência artificial? Os sinais para você não cair em conteúdo falso. Brasil Digital.",
    },
    "golpes": {
        "title": "Alerta de Golpe: IA e Segurança",
        "description": "Golpes com inteligência artificial, voz clonada, ataques hackers e vazamentos: o que está acontecendo e como se proteger. Brasil Digital.",
    },
    "novidades": {
        "title": "Novidades de IA e Tecnologia",
        "description": "As notícias reais de IA e tecnologia que mudam a vida do brasileiro, explicadas em menos de 1 minuto. Brasil Digital.",
    },
}

MAX_SHORT_SECONDS = 180
_REAL_OU_IA = re.compile(r"é real|é ia\b|feito por ia|falso|fake", re.I)
_GOLPES = re.compile(r"golpe|hacker|invad|ataque|senha|vazamento|vazou|clonad|segurança|espion|roub", re.I)


def series_for(content):
    key = (content.get("series") or "").strip()
    if key in SERIES:
        return key
    if content.get("category") == "ciberseguranca":
        return "golpes"
    return "novidades"


def _series_from_title(title):
    if _REAL_OU_IA.search(title):
        return "real-ou-ia"
    if _GOLPES.search(title):
        return "golpes"
    return "novidades"


def _find_playlist(youtube, key):
    wanted = SERIES[key]["title"].lower()
    request = youtube.playlists().list(part="snippet", mine=True, maxResults=50)
    while request is not None:
        response = request.execute()
        for item in response.get("items", []):
            if item["snippet"]["title"].strip().lower() == wanted:
                return item["id"]
        request = youtube.playlists().list_next(request, response)
    return None


def _find_or_create_playlist(youtube, key):
    """Retorna (playlist_id, criada_agora)."""
    playlist_id = _find_playlist(youtube, key)
    if playlist_id:
        return playlist_id, False
    info = SERIES[key]
    created = youtube.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {"title": info["title"], "description": info["description"], "defaultLanguage": "pt"},
            "status": {"privacyStatus": "public"},
        },
    ).execute()
    print(f"📚 Playlist criada: {info['title']} ({created['id']})")
    return created["id"], True


def _playlist_video_ids(youtube, playlist_id):
    ids = []
    request = youtube.playlistItems().list(part="contentDetails", playlistId=playlist_id, maxResults=50)
    while request is not None:
        response = request.execute()
        ids += [it["contentDetails"]["videoId"] for it in response.get("items", [])]
        request = youtube.playlistItems().list_next(request, response)
    return ids


def _insert(youtube, playlist_id, video_id, position=None, tries=6):
    # playlist recém-criada demora alguns segundos para "existir" na API (404 playlistNotFound),
    # e às vezes a API devolve 409 SERVICE_UNAVAILABLE — ambos passam sozinhos
    for attempt in range(tries):
        try:
            snippet = {"playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": video_id}}
            if position is not None:
                snippet["position"] = position
            youtube.playlistItems().insert(part="snippet", body={"snippet": snippet}).execute()
            return
        except Exception as e:
            transient = "playlistNotFound" in str(e) or "SERVICE_UNAVAILABLE" in str(e)
            if not transient or attempt == tries - 1:
                raise
            time.sleep(10)


def add_to_series(video_id, content):
    """Adiciona o Short na playlist da série dele. Nunca derruba a publicação."""
    try:
        from youtube_uploader import _get_client
        youtube = _get_client()
        key = series_for(content)
        playlist_id, _ = _find_or_create_playlist(youtube, key)
        _insert(youtube, playlist_id, video_id)
        print(f"📚 Adicionado à série '{SERIES[key]['title']}'")
    except Exception as e:
        print(f"⚠️  Não consegui adicionar à série: {e}")


def _seconds(iso):
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return ((d * 24 + h) * 60 + mi) * 60 + s


def _channel_shorts(youtube):
    """Shorts do canal (≤180s), do mais antigo pro mais novo."""
    channel = youtube.channels().list(part="contentDetails", mine=True).execute()["items"][0]
    uploads = channel["contentDetails"]["relatedPlaylists"]["uploads"]
    ids = _playlist_video_ids(youtube, uploads)
    shorts = []
    for i in range(0, len(ids), 50):
        response = youtube.videos().list(part="snippet,contentDetails,status", id=",".join(ids[i:i + 50])).execute()
        for v in response.get("items", []):
            if v["status"]["privacyStatus"] != "public" or _seconds(v["contentDetails"]["duration"]) > MAX_SHORT_SECONDS:
                continue
            shorts.append({"id": v["id"], "title": v["snippet"]["title"], "date": v["snippet"]["publishedAt"]})
    return sorted(shorts, key=lambda s: s["date"])


def backfill(youtube, apply=False):
    shorts = _channel_shorts(youtube)
    plan = {key: [s for s in shorts if _series_from_title(s["title"]) == key] for key in SERIES}
    for key, items in plan.items():
        print(f"\n📚 {SERIES[key]['title']} — {len(items)} Shorts")
        for s in items:
            print(f"   {s['date'][:10]}  {s['id']}  {s['title']}")
    if not apply:
        print("\n(só o plano — rode com --apply para inserir)")
        return

    for key, items in plan.items():
        if not items:
            continue
        playlist_id, created = _find_or_create_playlist(youtube, key)
        already = set() if created else set(_playlist_video_ids(youtube, playlist_id))
        added = position = 0
        for s in items:  # ordem cronológica = ordem dos episódios
            if s["id"] not in already:
                try:
                    _insert(youtube, playlist_id, s["id"], position)
                    already.add(s["id"])
                    added += 1
                except Exception as e:
                    print(f"⚠️  {s['id']}: {e}")
                    continue
            position += 1
        print(f"📚 {SERIES[key]['title']}: +{added} (total {len(already)}) → https://www.youtube.com/playlist?list={playlist_id}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if "--backfill" not in sys.argv:
        sys.exit("uso: python src/series.py --backfill [--apply]")
    from youtube_uploader import _get_client
    backfill(_get_client(), apply="--apply" in sys.argv)
