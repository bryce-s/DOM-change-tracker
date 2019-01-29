
from flask import Flask, redirect, url_for, session, request, jsonify, g
import subprocess
import flask
from flask_oauthlib.client import OAuth
import sqlite3
import re
import threading
from time import sleep
import smtplib


db_lock = threading.Lock()



DATABASE = 'database.db'

conn = sqlite3.connect(DATABASE)
try:
    conn.execute('CREATE TABLE tab (uid TEXT, link TEXT, img_link TEXT, in_stock TEXT, email TEXT)')
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


gmail_user = ""
gmail_password = ""
with open("email_info", "r") as inFile:
    for line in inFile:
        line = line.split(' ')
        gmail_user = line[0]
        gmail_password = line[1]





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
        db_lock.acquire()
        context = dict()
        user = google.get('userinfo')
        data = user.data
        uid = data['id']
        db = get_db()   
        cur = db.cursor()        
        if flask.request.method == 'POST':
            form = flask.request.form
            if 'delete' in form:
                # delete for now..
                delete_str = "delete from tab where uid = '" + str(uid) + "'"
                cur.execute(delete_str)
                db.commit()
                db_lock.release()
                return redirect(url_for('manage'))
            url = flask.request.values.get('targeturl') # Your form's
            item_name = flask.request.values.get('item_name')
            # # we'll just do an initial track here..
            # remove_query_string = url
            # if re.match(r'.+?[?]', url):
            #     remove_query_string = re.findall(r'.+?[?]', url)[0]
            #     remove_query_string = remove_query_string[:len(remove_query_string)-1]
            # target = "sh scripts/determine_if_in_stock.sh " + remove_query_string
            # res = subprocess.run(target,  None, capture_output=True, shell=True)
            # output = str(res.stdout)
            # output = output[2:len(output)-4]
            # in_stock = "in stock!"
            # if output == "not in stock":
            #     in_stock = "not in stock."
            # print(output)
            # print(res.stderr)
            cur.execute('insert into tab values (?, ?, ?, ?, ?)', (uid, url, item_name, 'AWAITING TRACK', data['email']))
            db.commit()            
            query = "select * from tab where uid = '" + str(uid) + "'"
            resulting_rows = cur.execute(query)
            rows = resulting_rows.fetchall()
            context['entries'] = rows
            db_lock.release()
            return flask.render_template('manage.html', **context)
        else:            
            query = "select * from tab where uid = '" + str(uid) + "'"
            resulting_rows = cur.execute(query)
            rows = resulting_rows.fetchall()
            context['entries'] = rows
            db_lock.release()
            return flask.render_template('manage.html', **context)
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


def db_track_wraper():
    with app.app_context():
        while True:
            sleep(60*10)

            db_lock.acquire()
            db = get_db()
            cur = db.cursor()
            query = cur.execute('select * from tab')
            rows = query.fetchall()
            db_lock.release()
            for row in rows: #lock again and try.. except to prevent a conflict. 
                url = row[1]
                uid = row[0]
                item_name = row[2]
                email = row[4]
                # we'll just do an initial track here..
                remove_query_string = url
                if re.match(r'.+?[?]', url):
                    remove_query_string = re.findall(r'.+?[?]', url)[0]
                    remove_query_string = remove_query_string[:len(remove_query_string)-1]
                target = "sh scripts/determine_if_in_stock.sh " + remove_query_string
                res = subprocess.run(target,  None, capture_output=True, shell=True)
                output = str(res.stdout)
                output = output[2:len(output)-4]
                in_stock = "IN STOCK"
                if output == "not in stock":
                    in_stock = "OUT OF STOCK"
                else:
                    sent_from = gmail_user  
                    to = [email]  
                    subject = 'OMG Super Important Message'  
                    body = item_name + " IS IN STOCK! BUY IT NOW! " + url + "\n" + "pls unsub at: http://127.0.0.1:5000/manage"

                    email_text = """\  
                    From: %s  
                    To: %s
                    Subject: %s

                    %s
                    """ % (sent_from, ", ".join(to), subject, body)
                    try:  
                        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
                        server.ehlo()
                        server.login(gmail_user, gmail_password)
                        server.sendmail(sent_from, to, email_text)
                        server.close()
                        print('Email sent!')
                    except:  
                        print('Something went wrong...')
                print(output)
                print(res.stderr)
                db_lock.acquire()
                target_str = "update tab set in_stock = '" + in_stock + "' where uid = '" + uid + "' and link = '" + url + "'" 
                try: 
                    cur.execute(target_str)
                    db.commit()
                except sqlite3.OperationalError as e:
                         print('mutexed db error--might be item was deleted after we searched')
                db_lock.release()

@app.before_first_request
def init_tracking():
    thread = threading.Thread(target = db_track_wraper)
    thread.start()
    print('tracking thread online.')


if __name__ == '__main__':
    app.run()

