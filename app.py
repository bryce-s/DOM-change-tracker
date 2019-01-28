"""
    google example
    ~~~~~~~~~~~~~~
    This example is contributed by Bruno Rocha
    GitHub: https://github.com/rochacbruno
"""
from flask import Flask, redirect, url_for, session, request, jsonify, g
import subprocess
import flask
from flask_oauthlib.client import OAuth
import sqlite3
import re


DATABASE = 'database.db'

conn = sqlite3.connect(DATABASE)
try:
    conn.execute('CREATE TABLE tab (uid TEXT, link TEXT, img_link TEXT, in_stock TEXT)')
except sqlite3.OperationalError as e:
    print('theres an error, we prob already made this table lol')
print('created tables~')


app = Flask(__name__)
app.config['GOOGLE_ID'] = "973475845576-q7pec39j0gipu0gd0v2m4c1ue2236dv6.apps.googleusercontent.com"
app.config['GOOGLE_SECRET'] = "wzcdsylEUNTeEwMuGOGgLKI7"
app.debug = True
app.secret_key = 'development'
oauth = OAuth(app)

google = oauth.remote_app(
    'google',
    consumer_key=app.config.get('GOOGLE_ID'),
    consumer_secret=app.config.get('GOOGLE_SECRET'),
    request_token_params={
        'scope': 'email'
    },
    base_url='https://www.googleapis.com/oauth2/v1/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
)

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/')
def index():
    # if 'google_token' in session:
    #     me = google.get('userinfo')
    #     return jsonify({"data": me.dta})
    # return redirect(url_for('login'))
    return flask.render_template('./startbootstrap-grayscale-gh-pages/index.html')


@app.route('/login')
def login():
    return google.authorize(callback=url_for('authorized', _external=True))


@app.route('/logout')
def logout():
    session.pop('google_token', None)
    return redirect(url_for('index'))

@app.route('/manage', methods=['GET', 'POST'])
def manage():
    if 'google_token' in session:
        context = dict()
        user = google.get('userinfo')
        data = user.data
        uid = data['id']
        db = get_db()   
        cur = db.cursor() 
        query = "select * from tab where uid = '" + str(uid) + "'"
        resulting_rows = cur.execute(query)
        rows = resulting_rows.fetchall()
        context['entries'] = rows
        print(resulting_rows)
        print(rows)
        if flask.request.method == 'POST':
            if flask.request.form and flask.request.form != 'targeturl':
                # we delet
                url = re.findall(r'_.+', str(flask.request.form))
                url = url[1:]


            url = flask.request.values.get('targeturl') # Your form's
            # we'll just do an initial track here..
            target = "sh scripts/determine_if_in_stock.sh " + url
            remove_query_string = re.findall('.+?[?]', url)[0]
            remove_query_string = remove_query_string[:len(remove_query_string)-1]
            res = subprocess.run(target,  None, capture_output=True, shell=True)
            output = str(res.stdout)
            output = output[2:len(output)-4]
            in_stock = "in stock!"
            if output == "not in stock":
                in_stock = "not in stock."
            print(output)
            print(res.stderr)
            cur.execute('insert into tab values (?, ?, ?, ?)', (uid, url, 'img_link', in_stock))
            db.commit()
            return flask.render_template('manage.html', **context)
        return flask.render_template('manage.html', **context)
    else:
        return redirect(url_for('login'))
# if google_token in session: me = google.get('userinfo')
# {
#   "data": {
#     "email": "bryces@umich.edu",
#     "hd": "umich.edu",
#     "id": "...",
#     "link": "https://plus.google.com/113292493455200231844",
#     "picture": "https://lh6.googleusercontent.com/-1hPDythOSRo/AAAAAAAAAAI/AAAAAAAABbs/V7BT-CGI0kk/photo.jpg",
#     "verified_email": true
#   }
# }
@app.route('/login/authorized')
def authorized():
    resp = google.authorized_response()
    if resp is None:
        return 'Access denied: reason=%s error=%s' % (
            request.args['error_reason'],
            request.args['error_description']
        )
    session['google_token'] = (resp['access_token'], '')
    me = google.get('userinfo')
    return redirect(url_for('manage'))


@google.tokengetter
def get_google_oauth_token():
    return session.get('google_token')


if __name__ == '__main__':
    app.run()

