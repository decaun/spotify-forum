from main.models import User, Post, Playlist, Song, load_user, PlaylistSchema, SongSchema, PostSchema
from main.forms import PostForm
from main import app,db,spotify
from flask import render_template,jsonify,request,url_for,redirect
from flask_login import login_user, current_user, logout_user
import spotipy


@app.route('/', methods = ['GET', 'POST'])
@app.route('/<int:playlist_id>', methods = ['GET', 'POST'])
@app.route('/<string:topic>/<int:playlist_id>', methods = ['GET', 'POST'])
def Topic(playlist_id=None,topic=None):
    if current_user.is_authenticated:
        print("Authenticated user")
        try:
            spotify.activate(current_user.access_token)
            me = spotify.active.me()#without this logout is not working properly. (verification for api access needed here)
        except Exception as e:
            print(e)
            logout_user()

        #try:
        #    spotify.call_playlists(current=0, next=50)
        #    spotify.insert_playlists(me['id'])
        #except Exception as e:
        #    #print(e)
        #    pass
    else:
        print("Non-authenticated user")

    form = PostForm()
    if form.validate_on_submit():
        try:
            spotify.insert_current_playlist(me['id'])
            spotify.insert_songs(spotify.current_playlist['local_id'])
        except:
            pass
        post = Post(title = 'test', content = form.content.data, user_id = current_user.id, playlist_id = spotify.current_playlist['local_id'] )
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('Topic', playlist_id=spotify.current_playlist['local_id']))
    return render_template('home.html',form=form)

@app.route('/logout')
def Logout():
    logout_user()
    return redirect(url_for('Topic'))

@app.route('/login')
def Login():
    try:
        me = spotify.active.me()
        real_user=User.query.filter_by(spotify_id=me['id']).first()
        user=load_user(real_user.id)
        spotify.activate(user.access_token)
        login_user(user, remember=True)
        return redirect(url_for('Topic'))
    except:
        return redirect(spotify.current_auth.get_authorize_url())

@app.route('/auth/',methods=['GET'])
def Auth():
    if request.method == 'GET':
        try:
            code = str(request.args['code'])
            token_info = spotify.current_auth.get_access_token(code)
            access_token = token_info['access_token']
            
        except Exception as e:
            print("Can not retrieve token")
            print(e)
            me = spotify.active.me()
            spotify.__init__()
            return redirect(url_for('Topic'))
        if access_token:
            try:
                spotify.activate(access_token)
            except:
                print("Authentication failed")
                logout_user()
                return redirect(url_for('Topic'))
            me = spotify.active.me()
            try:
                real_user=User.query.filter_by(spotify_id=me['id']).first()
                real_user.access_token=access_token
                db.session.commit()
                login_user(real_user, remember=True)
            except Exception as e:
                try:
                    user=User(spotify_id=me['id'], username=me['display_name'],email=me['email'],image_url=me['images'][0]['url'],access_token=access_token)
                    db.session.rollback()
                    db.session.add(user)
                    db.session.commit()
                except:
                    user=User(spotify_id=me['id'], username=me['display_name'],email=me['email'],access_token=access_token)
                    db.session.rollback()
                    db.session.add(user)
                    db.session.commit()
                login_user(user, remember=True)
            
        #next_page = request.args.get('next')
        #return redirect('next_page') if next_page else redirect(url_for('Topic'))

    return redirect(url_for('Topic'))

@app.route('/getplaylist',methods=['GET'])
def Playlist_data():
    if( request.headers['Selector']=='last' ):
        playlist_call = Playlist.query.with_entities(Playlist.id, Playlist.title, Playlist.genre).order_by(
                                Playlist.id.asc()).slice(
                                int(request.headers['Counter']), 5+int(request.headers['Counter'])).all()
    else:
        playlist_call = Playlist.query.with_entities(Playlist.id, Playlist.title, Playlist.genre).order_by(
                                Playlist.id.asc()).slice(
                                int(request.headers['Counter']), 1+int(request.headers['Counter'])).all()
    playlist_schema = PlaylistSchema(many=True)
    output = playlist_schema.dump(playlist_call).data
   
    return jsonify(output)

@app.route('/getsong',methods=['GET'])
def Song_data():
    song_call = Song.query.with_entities(Song.name, Song.album, Song.artist, Song.popularity,
                                Song.danceability, Song.energy, Song.key, Song.tempo,
                                Song.time_signature).filter_by(
                                playlist_id=int(request.headers['Playlist-ID'])).slice(
                                int(request.headers['Counter']), 5+int(request.headers['Counter'])).all()
    song_schema = SongSchema(many=True)
    output = song_schema.dump(song_call).data
    if int(request.headers['Counter'])==0:
        spotify.current_playlist={'local_id':int(request.headers['Playlist-ID'])}
    
    return jsonify(output)

@app.route('/getpost',methods=['GET'])
def Post_data():
    #.with_entities("author",Post.title, Post.content, Post.date_posted, Post.user_id)
    #.options(lazyload("author"))
    #Post.query.options(joinedload(Post.author).joinedload(User.username,innerjoin=True)).with_entities(User.username,Post.title, Post.content, Post.date_posted, Post.user_id).all()
    post_call = db.session.query(Post).filter_by(
                                playlist_id=int(request.headers['Playlist-ID'])).join(User).with_entities(
                                User.username,Post.content,Post.title, Post.date_posted, Post.user_id).slice(
                                int(request.headers['Counter']), 5+int(request.headers['Counter'])).all()
    post_schema = PostSchema(many=True)
    output = post_schema.dump(post_call).data
   
    return jsonify(output)

@app.route('/cachedplaylist',methods=['GET'])
def Cached_playlist_data(playlist_id=None):
    if current_user.is_authenticated:
        print(request.headers['Counter'])
        try:
            spotify.playlists=None
            spotify.call_playlists(current=int(request.headers['Counter']), next=5)
        except Exception as e:
            #print(e)
            pass
        return jsonify(spotify.playlists)

@app.route('/cachedsong',methods=['GET'])
def Cached_song_data(playlist_id=None):
    if current_user.is_authenticated:
        #http://127.0.0.1/cachedsong?user_id=11101365382&&playlist_id=5w6x6mmaVU4sPouB2MBoMN&&start=0&&count=1
        if int(request.args.get('count'))<=100:
            spotify.call_songs(request.args.get('user_id'),request.args.get('playlist_id'), current=int(request.args.get('start')), next=int(request.args.get('count')))
        else:
            for counter in range(0,int(request.args.get('count')),100):
                print(counter)
                spotify.call_songs(request.args.get('user_id'),request.args.get('playlist_id'), current=counter, next=100)#max range for api hardcoded as 100

        #print(request.args.get('user_id'))
        #print(request.args.get('playlist_id'))
        spotify.call_tags(request.args.get('playlist_id'))
        
        #print(spotify.current_playlist_tags)
        spotify.songs.update({'genres': spotify.current_playlist_tags})
        spotify.set_user_current_playlist(request.args.get('user_id'),request.args.get('playlist_id'))
        #print(spotify.current_playlist)

        return jsonify(spotify.songs)
    pass

