import requests
import os
import sqlite3 as lite
import sys  
import json
import time
from datetime import datetime
from dateutil import parser
from flask import Flask, request, jsonify, json, render_template

app = Flask(__name__)

con = None
global_url = "https://github.com/golang/go/issues"
# message_count = 0
@app.template_filter()
def datetimefilter(value, format='%H:%M'):
    """convert a datetime to a different format."""
    a = parser.parse(value)
    return a.strftime(format)

app.jinja_env.filters['datetimefilter'] = datetimefilter

@app.cli.command()
def initdb_command():
    """Initializes the database."""
    con = lite.connect('user.db')
    with con:
        cur = con.cursor()
        cur.execute("CREATE TABLE Threads(profile_image VARCHAR, user_token VARCHAR, fname TEXT, lname TEXT, msg_text VARCHAR, msg_timestamp DATETIME, parent_msg_id VARCHAR)")
    
    print('Initialized the database.')

@app.route('/events', methods=['POST'])
def app_install():
    req = request.get_data()
    print req
    json_request = json.loads(req)
    print json_request
    if json_request.get('name') == 'app.install':
        con = lite.connect('user.db')
        user_id = json_request.get('userId')
        user_token = json_request.get('userToken')
        user_name = ''
        user_data = [user_id,user_token, user_name]
        with con:
 
            cur = con.cursor()  
            # cur.execute("CREATE TABLE Users(user_id VARCHAR, user_token VARCHAR, name TEXT)")
            cur.execute("INSERT INTO Users VALUES(?,?,?)", user_data)
            # con.close()
    return jsonify({"status":200})

@app.route('/threads', methods=['POST','GET'])
def threads():    
    print request.args
    flock_event_dict = request.args.get('flockEvent')
    flock_event_dict = json.loads(flock_event_dict)
    user_id = flock_event_dict["userId"]
    message_uid = flock_event_dict["messageUids"]["messageUid"]
    # print '*'*50
    chat_id = flock_event_dict["chat"]
    print chat_id
    # print message_uid
    # print '*'*50
    chat = flock_event_dict["chat"]
    
    con = lite.connect('user.db')
    with con:
        cur = con.cursor()
        
        res = cur.execute("SELECT user_token FROM Users WHERE user_id=?", (user_id,))
        user_token = res.fetchone()[0]
        payload = {"token": user_token}
        res = requests.get('https://api.flock.co/v1/users.getInfo', params=payload)
        response = res.json()
        invoker_profile_image = response.get('profileImage')
        invoker_token = user_token
        invoker_first_name = response.get('firstName')
        invoker_last_name = response.get('lastName')

        payload = {"token": user_token, "chat":chat , "uids":"[\"{}\"]".format(message_uid)}
        res = requests.get('https://api.flock.co/v1/chat.fetchMessages', params=payload)

        response = res.json()[0]
        creator_id = response['from']
        text = response['text']
        parent_msg_id = response['uid']
        payload = {}

        res = cur.execute("SELECT user_token FROM Users WHERE user_id=?", (creator_id,))
        creator_token = res.fetchone()[0]
        payload = {"token": creator_token}
        res = requests.get('https://api.flock.co/v1/users.getInfo', params=payload)
        response = res.json()
        first_name = response.get('firstName')
        last_name = response.get('lastName')
        profile_image = response.get('profileImage')
        timestamp = response.get('timestamp')
        timestamp = time.strftime('%H:%M', time.localtime(timestamp))

        res = cur.execute("SELECT * FROM Threads WHERE parent_msg_id=?", (parent_msg_id,))
        
        previous_messages = res.fetchall()
        

    return render_template('threads.html', data_dict ={'creator':
        {'firstName':first_name, 'lastName': last_name, 'profileImage': profile_image, 'text':text, 'timestamp':timestamp, 'parent_msg_id': parent_msg_id, 'previous_messages': previous_messages, 'creator_id':creator_id, 'creator_token':creator_token, 'chat_id':chat_id},
        'invoker':{'invoker_token':invoker_token, 'invoker_profile_image':invoker_profile_image, 'invoker_first_name': invoker_first_name, 'invoker_last_name':invoker_last_name}})



@app.route('/save_message', methods=['POST'])
def save_to_db():
    print request.form
    print type(request.form)
    # return jsonify({'status':200})
    json_request = request.form
    message_data = []
    message_data.append(json_request.get('profile_image'))
    message_data.append(json_request.get('invoker_token'))
    message_data.append(json_request.get('fname'))
    message_data.append(json_request.get('lname'))
    message_data.append(json_request.get('msg_txt'))
    message_data.append(json_request.get('msg_timestamp'))
    message_data.append(json_request.get('parent_msg_id'))

    print message_data

    con = lite.connect('user.db')
    with con:
        cur = con.cursor()
        cur.execute("INSERT INTO Threads VALUES(?,?,?,?,?,?,?)", message_data)
    return jsonify({'status':200})

@app.route('/send_message', methods=['POST'])
def send_message():
    chat_id = request.form['chat_id']
    creator_token = request.form['creator_token']
    parent_msg_id = request.form['parent_msg_id']

    con = lite.connect('user.db')
    with con:
        cur = con.cursor()
        res = cur.execute("SELECT count(parent_msg_id) FROM Threads WHERE parent_msg_id=?", (parent_msg_id,))
         # message_count
        message_count = res.fetchone()[0]
        print '*'*20
        print 'inside sned'
        print message_count
        # print res.fetchone()20
        print '*'*20
    # payload = {"to": chat_id, "token":creator_token, "attachments": "[{"views":{"widget":{"src":"http://b63e8435.ngrok.io/user_count","width": 200,"height": 40}}}]"}
    payload = {"to":chat_id,"token":creator_token,"attachments":"[{\"views\":{\"widget\":{\"src\":\"http://b63e8435.ngrok.io/user_count?message_count=%s\",\"width\": 200,\"height\": 40}}}]" %message_count}
    print 'befre req'
    res = requests.get('https://api.flock.co/v1/chat.sendMessage', params=payload)
    print 'after req'
    print res.url

    return jsonify({'status':200})

@app.route('/user_count', methods=['GET'])
def user_count():
    return render_template('count.html', data=request.args['message_count'])


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    # app.run(host='0.0.0.0', port=port)
    app.run(host='0.0.0.0', port=port,debug=True, threaded=True)