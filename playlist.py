from typing import List
import spotipy
from spotipy.oauth2 import SpotifyPKCE
from pathlib import Path
import json
from pykick import shows, Show
import asyncio
import random

AUTH_FILE = Path(__file__).parent / "auth.json"
MAX_IDS_PER_ADD = 100
PLAYLIST_NAME = "SF Upcoming"

with open(AUTH_FILE) as f:
    auths = json.load(f)

auth_manager = SpotifyPKCE(
    client_id= auths["id"],
    redirect_uri=auths["url"],
    scope=["playlist-modify-public","user-library-read"],
)

sp = spotipy.Spotify(
    auth_manager=auth_manager,
)

def get_tracks(show: Show, pick: int=3) -> List[str]:
    results = sp.search(q=show.artist, limit=1, offset=0, type="artist", market="US")
    if len(results['artists']) < 1:
        return []

    artist = results['artists']['items'][0]
    tracks_result = sp.artist_top_tracks(artist_id=artist['uri'], country="US")

    tracks = tracks_result['tracks']
    pick = min(pick, len(tracks))

    ids = []
    for _ in range(pick):
        i = random.randint(0, pick - len(ids)-1)
        ids.append(tracks.pop(i)['id'])
    
    return ids

sf_shows = asyncio.run(shows(limit=100,days=14))
tracks = [
    track for show in sf_shows for track in get_tracks(show=show, pick=3) 
]

playlist = sp.user_playlist_create(
    user=auths["user"],
    name=PLAYLIST_NAME,
    public=True,
    collaborative=False,
    description="Artists with shows coming up around the San Fransisco Bay",
)

for chuck_i in range(int(len(tracks) / MAX_IDS_PER_ADD)):
    chunk_start = MAX_IDS_PER_ADD * chuck_i
    sp.user_playlist_add_tracks(
        user=auths["user"],
        playlist_id=playlist["id"],
        tracks=tracks[chunk_start:(chunk_start + MAX_IDS_PER_ADD - 1)],
    )
