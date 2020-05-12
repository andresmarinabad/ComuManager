import os
from flask import Flask, redirect, url_for, request, render_template
from flask_mail import Mail, Message
from pymongo import MongoClient
import random
from firebase import firebase

app = Flask(__name__)

mail_settings = {
    "MAIL_SERVER": 'smtp.gmail.com',
    "MAIL_PORT": 465,
    "MAIL_USE_TLS": False,
    "MAIL_USE_SSL": True,
    "MAIL_USERNAME": os.environ['EMAIL_USER'],
    "MAIL_PASSWORD": os.environ['EMAIL_PASSWORD']
}

app.config.update(mail_settings)
mail = Mail(app)

client = MongoClient(os.environ['MONGODB_HOST'])
db = client.comu
lista = []

firebase = firebase.FirebaseApplication(os.environ['FIREBASE_URL'], None)
firebase_collection = os.environ['FIREBASE_COLLECTION']


class Hermano:
    def __init__(self, name, num):
        self.name = name
        self.num = num

class Grupo:
    def __init__(self, id):
        self.id = id
        self.hermanos = []
        self.many = 0

    def add_member(self, member):
        self.hermanos.append(member)
        self.many += int(member.num)


@app.route('/')
def comu():
    global lista
    lista = []
    _items = db.list.find()
    _groups = db.groups.find()

    items = [item for item in _items]
    for hermano in items:
        lista.append(Hermano(hermano['name'], hermano['num']))

    groups = [group for group in _groups]

    return render_template('index.html', items=items, groups=groups)


@app.route('/remove', methods=['POST'])
def remove():
    item_doc = {'name': request.form['name']}
    db.list.delete_one(item_doc)

    return redirect(url_for('comu'))


@app.route('/groups', methods=['POST'])
def groups():

    global lista
    db.groups.delete_many({})
    num_hermanos = request.form['num_groups']
    if num_hermanos == '':
        num_hermanos = 5

    # local_list = lista.copy()
    local_list = lista[:]

    random.shuffle(local_list)
    groups = []
    id_grupo = 1
    while (len(local_list) > 0):
        if (len(groups) == 0):
            groups.append(Grupo(id_grupo))
            id_grupo += 1
        if (groups[-1].many < int(num_hermanos)):
            hermano = local_list[0]
            groups[-1].add_member(hermano)
            local_list.pop(0)
        else:
            groups.append(Grupo(id_grupo))
            id_grupo += 1

    if (groups[-1].many < int(num_hermanos)):
        # local_list = lista.copy()
        local_list = lista[:]
        random.shuffle(local_list)
        while (groups[-1].many < int(num_hermanos)):
            hermano = local_list[0]

            if (hermano not in groups[-1].hermanos):
                groups[-1].add_member(hermano)
            local_list.pop(0)

    for group in groups:
        names = [hermano.name for hermano in group.hermanos]
        item_doc = {
            'id': group.id,
            'hermanos': ','.join(names)
        }
        db.groups.insert_one(item_doc)
    return redirect(url_for('comu'))


@app.route('/export', methods=['POST'])
def exportar():
    result = firebase.get(firebase_collection, '')
    if result is not None:
        for id_child in result:
            firebase.delete(firebase_collection, id_child)
    _groups = db.groups.find()
    groups = [group for group in _groups]
    for group in groups:
        data = {int(group['id']): group['hermanos']}
        firebase.post(firebase_collection, data)

    return redirect(url_for('comu'))


@app.route('/add', methods=['POST'])
def add():

    item_doc = {
        'name': request.form['name'],
        'num': request.form['num']
    }
    db.list.insert_one(item_doc)

    return redirect(url_for('comu'))


@app.route('/send', methods=['POST'])
def send_email():
    _groups = db.groups.find()
    groups = [group for group in _groups]
    msg = Message(subject="ComuManager: Grupos",
                  sender=app.config.get("MAIL_USERNAME"),
                  recipients=[app.config.get("MAIL_USERNAME")],
                  body=render_template('email.html', groups=groups))
    mail.send(msg)
    return redirect(url_for('comu'))


@app.errorhandler(404)
def page_not_found(e):
    return render_template('error/404.html'), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return render_template('error/405.html'), 405


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error/500.html'), 500


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=False)
