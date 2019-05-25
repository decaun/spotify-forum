from main.models import User, Post, Playlist, Song
from main import db
import spotipy
from spotipy import oauth2


SPOTIPY_CLIENT_ID = '83a29879ab1b4e76acb763bb3f2d8bcc'
SPOTIPY_CLIENT_SECRET = '1cc669adfa30443dbcf25eb52e43dbda'
SPOTIPY_REDIRECT_URI = 'http://127.0.0.1:80/auth/'


class SpotifyApi():
    
    def __init__(self):
        self.SCOPE = 'user-read-private user-read-email user-library-read user-top-read playlist-read-private playlist-read-collaborative'
        self.CACHE = None#'.spotipyoauthcache' if disabled no cache generated at backend ( no cache needed if you store token at DB == no cache management :) )
        self.active=None
        self.playlists=None
        self.songs=None
        self.features=[]
        self.current_playlist_tags=[]
        self.current_playlist=None
        self.current_auth = oauth2.SpotifyOAuth( SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET,
                                                SPOTIPY_REDIRECT_URI,scope=self.SCOPE,
                                                cache_path=self.CACHE )
    

    def activate(self,access_token):
        self.active = spotipy.Spotify(access_token)

    def call_playlists(self, current=0, next=5):
        if self.playlists==None or len(self.playlists['items'])<next:
            self.playlists=self.active.current_user_playlists(limit=next, offset=current)#limit max 50 need to offset after 50 for next 50
            for playlist in range(0,len(self.playlists['items'])):
                    self.playlists['items'][playlist].update({'genres': []})#need refactor (green) issue with overwritten genre objects
            

    def call_songs(self, user_id, spotify_playlist_id, 
                    current=0, next=5):
        #self.current_playlist=spotify_playlist_id
        if current==0:
            self.songs=self.active.user_playlist_tracks(user_id, playlist_id=spotify_playlist_id, 
                                                        fields=None, limit=next, offset=current, 
                                                        market=None)#limit max 100 need to offset after 100 for next 100
        else:
            #current_song_size=len(self.songs['items'])
            data_holder=self.active.user_playlist_tracks(user_id, playlist_id=spotify_playlist_id, 
                                                        fields=None, limit=next, offset=current, 
                                                        market=None)#limit max 100 need to offset after 100 for next 100
            for song in range(0,len(data_holder['items'])):
                self.songs['items'].append(data_holder['items'][song])

        self.call_features()
        #self.call_tags(spotify_playlist_id)#should be removed from here later
        #self.insert_tag(user_id)#should be removed from here later

    def call_features(self):
        list_of_tracks=[]
        self.features=[]
        for song in range(0,len(self.songs['items'])):
            list_of_tracks.append(str(self.songs['items'][song]['track']['id']))
            
        for batch in range(0,len(list_of_tracks),100):
            self.features+=self.active.audio_features(tracks = list_of_tracks[batch:batch+100])

        for song in range(0,len(self.songs['items'])):
            self.songs['items'][song].update({'features': self.features[song]})

    
    def call_tags(self, spotify_playlist_id):
        track_ids=set()
        for song in range(0,len(self.songs['items'])):
            if len(track_ids)<50:#hardcoded limit for tag lookup related artist API
                track_ids.add(self.songs['items'][song]['track']['album']['artists'][0]['id'])
        artists=self.active.artists(track_ids)
        genres={}
        for track in range(0,len(track_ids)):
            for genre in artists['artists'][track]['genres']:
                if genre in genres:
                    genres[genre]+=1
                else:
                    genres.update({genre:1})

        if genres:
            genres=sorted(genres.items(),key=lambda genres:genres[1],reverse=True)
            genres=[list(genres) for genres in zip(*genres)][0]
            for playlist in range(0,len(self.playlists['items'])):
                if self.playlists['items'][playlist]['id']==spotify_playlist_id:
                    self.playlists['items'][playlist]['genres']=genres
            self.current_playlist_tags=genres
            #print(self.current_playlist_tags)

    def insert_tag(self):
        tag_to_db=Playlist.query.filter_by(spotify_id=self.current_playlist['id']).first()
        if tag_to_db.genre==None:
            try:
                tag_to_db.genre=self.current_playlist_tags[0]
                db.session.commit()
            except Exception as e:
                print(e)
                db.session.rollback()
                pass


    def insert_playlists(self,user_id):
        for playlist in range(0,len(self.playlists['items'])):
            playlist_to_db=Playlist(spotify_id=self.playlists['items'][playlist]['id'], 
                                title=self.playlists['items'][playlist]['name'],
                                user_id=user_id)
            playlist_from_db=Playlist.query.filter_by(spotify_id=playlist_to_db.spotify_id,
                                                    user_id=user_id).first()
            #print(playlist)
            if playlist_from_db!=None:
                pass
            else:
                try:
                    db.session.add(playlist_to_db)
                    db.session.commit()
                except Exception as e:
                    print(e)
                    db.session.rollback()

    def insert_current_playlist(self,local_user_id):
        #not tested
        playlist_to_db=Playlist(spotify_id=self.current_playlist['id'], 
                            title=self.current_playlist['name'],
                            user_id=local_user_id,
                            genre=self.current_playlist_tags[0])
        playlist_from_db=Playlist.query.filter_by(spotify_id=playlist_to_db.spotify_id).first()
        #print(playlist)
        if playlist_from_db!=None:
            pass
        else:
            try:
                db.session.add(playlist_to_db)
                db.session.commit()
                db.session.refresh(playlist_to_db)
                self.current_playlist={'local_id':playlist_to_db.id}
            except Exception as e:
                print(e)
                db.session.rollback()


    def insert_songs(self, playlist_id):
        #not tested
        for song in range(0,len(self.songs['items'])):
            song_to_db=Song(order = song,
                        spotify_id = self.songs['items'][song]['track']['id'], 
                        name = self.songs['items'][song]['track']['name'], 
                        album = self.songs['items'][song]['track']['album']['name'],
                        artist = self.songs['items'][song]['track']['album']['artists'][0]['name'],
                        popularity = self.songs['items'][song]['track']['popularity'],
                        playlist_id = playlist_id,
                        danceability = self.songs['items'][song]['features']['danceability'],#alternative-danceability = self.features[song]['features']['danceability'],
                        energy = self.songs['items'][song]['features']['energy'],
                        key = self.songs['items'][song]['features']['key'],
                        mode = self.songs['items'][song]['features']['mode'],
                        speechiness = self.songs['items'][song]['features']['speechiness'],
                        acousticness =self.songs['items'][song]['features']['acousticness'],
                        instrumentalness =self.songs['items'][song]['features']['instrumentalness'],
                        liveness = self.songs['items'][song]['features']['liveness'],
                        valence = self.songs['items'][song]['features']['valence'],
                        tempo = self.songs['items'][song]['features']['tempo'],
                        uri = self.songs['items'][song]['features']['uri'],
                        time_signature = self.songs['items'][song]['features']['time_signature'])

            song_from_db=Song.query.filter_by(spotify_id=song_to_db.spotify_id,
                                                playlist_id=playlist_id).first()
            if song_from_db!=None:
                song_from_db=Song.query.filter_by(playlist_id=playlist_id,
                                                order=song).first()
                if song_from_db!=None:
                    if song_from_db.spotify_id!=song_to_db.spotify_id:
                        #if there is difference at song orders or different songs added etc. here i delete rest of rows bellow (> asc order)!!!
                        try:
                            Song.query.filter(Song.id >= song_from_db.id).delete()
                            db.session.commit()
                            db.session.add(song_to_db)
                            db.session.commit()
                        except Exception as e:
                            print(e)
                            db.session.rollback()
            else:
                try:
                    db.session.add(song_to_db)
                    db.session.commit()
                except Exception as e:
                    print(e)
                    db.session.rollback()

    def set_user_current_playlist(self,spotify_user_id,spotify_playlist_id):
        self.current_playlist=self.active.user_playlist(spotify_user_id, playlist_id=spotify_playlist_id, fields=None)
