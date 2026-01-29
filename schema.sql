-- schema.sql
CREATE TABLE IF NOT EXISTS albums (
    album_id TEXT PRIMARY KEY,
    album_name TEXT NOT NULL,
    album_release_date TEXT,
    album_release_date_precision TEXT,
    album_total_tracks INTEGER,
    album_image_url TEXT,
    album_spotify_url TEXT,
    ablum_uri TEXT,
    album_type TEXT
);

CREATE TABLE IF NOT EXISTS tracks (
    played_at TEXT PRIMARY KEY,
    track_id TEXT NOT NULL,
    track_name TEXT NOT NULL,
    track_popularity INTEGER,
    track_duration_ms INTEGER,
    track_explicit BOOLEAN,
    track_disc_number INTEGER,
    track_number INTEGER,
    track_type TEXT,
    track_href TEXT,
    track_isrc TEXT,
    track_uri TEXT,
    track_spotify_url TEXT,
    album_id TEXT,
    FOREIGN KEY (album_id) REFERENCES albums(album_id)
);

CREATE TABLE IF NOT EXISTS artists (
    artist_id TEXT PRIMARY KEY,
    artist_name TEXT NOT NULL,
    artist_url TEXT,
    artist_type TEXT
);

CREATE TABLE IF NOT EXISTS track_artists (
    played_at TEXT NOT NULL,
    artist_id TEXT NOT NULL,
    artist_position INTEGER,
    PRIMARY KEY (played_at, artist_id),
    FOREIGN KEY (played_at) REFERENCES tracks(played_at) ON DELETE CASCADE,
    FOREIGN KEY (artist_id) REFERENCES artists(artist_id)
);

CREATE INDEX IF NOT EXISTS idx_track_artists_artist ON track_artists(artist_id);
CREATE INDEX IF NOT EXISTS idx_tracks_album ON tracks(album_id);
CREATE INDEX IF NOT EXISTS idx_tracks_played_at ON tracks(played_at DESC);