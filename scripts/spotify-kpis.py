import os
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Load .env variables
load_dotenv()

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URL')  # fix key name to match .env

# Authenticate with Spotify using spotipy
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope="user-top-read"
))

def get_top_items(item_type="artists", time_range="short_term", limit=10):
    if item_type == "artists":
        return sp.current_user_top_artists(time_range=time_range, limit=limit)["items"]
    elif item_type == "tracks":
        return sp.current_user_top_tracks(time_range=time_range, limit=limit)["items"]
    else:
        raise ValueError("Invalid item_type. Use 'artists' or 'tracks'.")


def print_top_artists(artists):
    print("\n Top Artists:")
    for i, artist in enumerate(artists, start=1):
        print(f"{i}. {artist['name']}")

def print_top_tracks(tracks):
    print("\n Top Tracks:")
    for i, track in enumerate(tracks, start=1):
        artist_names = ", ".join([artist["name"] for artist in track["artists"]])
        print(f"{i}. {track['name']} - {artist_names}")

if __name__ == "__main__":
    top_artists = get_top_items("artists", time_range="medium_term", limit=5)
    top_tracks = get_top_items("tracks", time_range="medium_term", limit=5)

    print_top_artists(top_artists)
    print_top_tracks(top_tracks)
