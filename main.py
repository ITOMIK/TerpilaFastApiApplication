import os
import uuid
import random

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests
import yt_dlp
from youtubesearchpython import VideosSearch
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

with open(".env") as f:
    for line in f:
        k, v = line.split("=")
        os.environ[k] = v

LASTFM_API_KEY = os.environ.get("LASTFM_API_KEY").strip()
LASTFM_API_URL = "http://ws.audioscrobbler.com/2.0/"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "https://music-application-react-terpila.onrender.com"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


class Song:
    id: int
    name: str
    artist: str
    url: str

    def __init__(self, _name, _artist, _url):
        self.id = uuid.uuid4()
        self.name = _name
        self.artist = _artist
        self.url = _url


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = "default-src *; connect-src *; script-src *; object-src *;"
    response.headers["X-Content-Security-Policy"] = "default-src *; connect-src *; script-src *; object-src *;"
    response.headers[
        "X-Webkit-CSP"] = "default-src *; connect-src *; script-src 'unsafe-inline' 'unsafe-eval' *; object-src *;"
    return response


@app.get("/")
async def root():
    return {"as": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"sss": f"Hello {name}"}


@app.get("/GetTrackInfo/{name}")
async def _get_youtube_link(name: str):
    _n = await search_track(name)
    print(_n)
    url = await get_youtube_link(_n)
    result = Song(_url=url, _artist=_n.split(" - ")[0], _name=_n.split(" - ")[1])
    return result


@app.get("/GetMp3Link/{url}")
async def _get_mp3_link(url: str):
    headers = {
        "Access-Control-Allow-Origin": "*",  # Разрешить доступ из любых источников
        "Access-Control-Allow-Methods": "GET, POST",  # Разрешить только GET и POST методы
        "Access-Control-Allow-Headers": "X-Custom-Header",  # Разрешить только определённые заголовки
    }
    url = "https://www.youtube.com/watch?v=" + url
    song_info = yt_dlp.YoutubeDL({'format': 'bestaudio/best', 'verbose': True}).extract_info(url, download=False)
    _url = song_info['formats'][0]['url']
    return JSONResponse({"url": _url}, headers=headers)


@app.get("/GetChart")
async def _get_chart():
    chart = await get_chart()
    result = []
    print(chart)
    for i in chart:
        print(i)
        result.append(
            Song(_name=i["track"], _url=await get_youtube_link(i["artist"] + " " + i["track"]),
                 _artist=i["artist"]))

    return result


@app.get("/GetTopTracks/{userName}")
async def __get_chart(userName: str):
    chart = await get_top_tracks(userName)
    result = []
    print(chart)
    for i in chart:
        print(i)
        result.append(
            Song(_name=i["track"], _url=await get_youtube_link(i["artist"] + " " + i["track"]), _artist=i["artist"]))

    return result


@app.get("/GetAlbumTracks/{name}")
async def __get_chart(name: str):
    r = await  search_album(name)
    print(r)
    if (not r):
        return
    chart = await get_album_tracks(r.split("\t")[0], r.split("\t")[1])
    result = []
    print(chart)
    for i in chart:
        print(i)
        a = await get_youtube_link(r.split("\t")[0] + " " + i)
        result.append(
            Song(_name=i, _url=a,
                 _artist=r.split("\t")[0]))

    return result


@app.get("/SearchAlbums/{albumname}")
async def __search_album(albumname):
    base_url = "http://ws.audioscrobbler.com/2.0/"
    method = "album.search"
    params = {
        "album": albumname,
        "api_key": LASTFM_API_KEY,
        "method": method,
        "format": "json"
    }
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Raise an HTTPError for bad responses

        data = response.json()
        result = data["results"]["albummatches"]["album"]
        print(data)
        _result = []
        if len(result) > 0:
            max_ = 0
            for i in result:
                max_ += 1
                answ = i["name"] + " " + i["artist"]
                _result.append(answ)
                if (max_ > 3):
                    break
            return _result

    except requests.exceptions.RequestException as e:
        print(f"Error during API request: {e}")
        return None


@app.get("/SearchTrack/{track_name}")
async def __search_track(track_name):
    params = {
        "method": "track.search",
        "track": track_name,
        "api_key": LASTFM_API_KEY,
        "format": "json"
    }
    try:
        response = requests.get(LASTFM_API_URL, params=params)
        response.raise_for_status()  # Проверяем статус ответа
        data = response.json()
        # Извлекаем имя исполнителя и название первого трека из результатов поиска
        print(data["results"]["trackmatches"]["track"])
        result = [i["artist"] + " " + i["name"] for i in data["results"]["trackmatches"]["track"]]
        return result[0:4]
    except (requests.exceptions.RequestException, IndexError) as e:
        print("Error:", e)
        return None


async def get_youtube_link(name):
    if name:
        videos_search = VideosSearch(f"{name}", limit=1)
        results = videos_search.result()

        if 'result' in results and results['result']:
            youtube_link = results['result'][0]['link']
            return youtube_link.split("=")[1]
    return None


async def search_track(track_name):
    params = {
        "method": "track.search",
        "track": track_name,
        "api_key": LASTFM_API_KEY,
        "format": "json"
    }
    try:
        response = requests.get(LASTFM_API_URL, params=params)
        response.raise_for_status()  # Проверяем статус ответа
        data = response.json()
        # Извлекаем имя исполнителя и название первого трека из результатов поиска
        artist = data["results"]["trackmatches"]["track"][0]["artist"]
        track = data["results"]["trackmatches"]["track"][0]["name"]
        result = f"{artist} - {track}"
        return result
    except (requests.exceptions.RequestException, IndexError) as e:
        print("Error:", e)
        return None


async def get_album_tracks(artist, album):
    params = {
        "method": "album.getinfo",
        "api_key": LASTFM_API_KEY,
        "artist": artist,
        "album": album,
        "format": "json",
    }
    try:
        response = requests.get(LASTFM_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        tracks = data["album"]["tracks"]["track"]
        return [track["name"] for track in tracks]
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None


async def get_chart():
    base_url = "http://ws.audioscrobbler.com/2.0/"
    method = "chart.gettoptracks"
    params = {
        "api_key": LASTFM_API_KEY,
        "method": method,
        "format": "json"
    }

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Raise an HTTPError for bad responses

        data = response.json()
        tracks = data["tracks"]["track"]
        result = [{"artist": track["artist"]["name"], "track": track["name"]} for track in tracks]
        random.shuffle(result)
        return result

    except requests.exceptions.RequestException as e:
        print(f"Error during API request: {e}")
        return None


async def get_top_tracks(username):
    base_url = "http://ws.audioscrobbler.com/2.0/"
    method = "user.gettoptracks"
    params = {
        "user": username,
        "api_key": LASTFM_API_KEY,
        "method": method,
        "format": "json"
    }

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Raise an HTTPError for bad responses

        data = response.json()
        tracks = data["toptracks"]["track"]

        # Extracting relevant information
        result = [{"artist": track["artist"]["name"], "track": track["name"]} for track in tracks]

        # Shuffle the list randomly
        random.shuffle(result)

        return result

    except requests.exceptions.RequestException as e:
        print(f"Error during API request: {e}")
        return None


async def search_album(albumname):
    base_url = "http://ws.audioscrobbler.com/2.0/"
    method = "album.search"
    params = {
        "album": albumname,
        "api_key": LASTFM_API_KEY,
        "method": method,
        "format": "json"
    }
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Raise an HTTPError for bad responses

        data = response.json()
        result = data["results"]["albummatches"]["album"]
        print(data)
        if (len(result) > 0):
            for key, value in rightNamesOfTracks.items():
                if (result[0]["name"].startswith(key)):
                    result[0]["name"] = value
            answ = result[0]["artist"] + "\t" + result[0]["name"]
            return answ

    except requests.exceptions.RequestException as e:
        print(f"Error during API request: {e}")
        return None


rightNamesOfTracks = {
    "8 Cпособов": "8 Способов Как Бросить ...",
    "8 способов": "8 Способов Как Бросить ...",
    "Очень страшная Молли": "ОЧЕНЬ СТРАШНАЯ МОЛЛИ 3, Ч. 1 - EP"

}
