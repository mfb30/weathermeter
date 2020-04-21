import requests
from azure.cosmos import *
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import azure.cosmos.cosmos_client as cosmos_client
import azure.cosmos.errors as errors
import azure.cosmos.http_constants as http_constants

import os
url = 'https://mfb30.documents.azure.com:443/'
key ='gDFt8v1nkfKuz1xNSnYxJ8frO4oOcjpxeEAP0gjCkoYjNSfdACZnMPT5k3CUivgoezhiXp0WIFVpO4PvsRsFIw=='
client = cosmos_client.CosmosClient(url, {'masterKey': key})
app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///weather.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'thisisasecret'

db = SQLAlchemy(app)
database_name = 'CloudDataBase'
try:
    database = client.CreateDatabase({'id': database_name})
except errors.HTTPFailure:
    database = client.ReadDatabase("dbs/" + database_name)
import azure.cosmos.documents as documents
container_definition = {'id': 'weathercontainer',
                        'partitionKey':
                                    {
                                        'paths': ['/productName'],
                                        'kind': documents.PartitionKind.Hash
                                    }
                        }
try:
    container = client.CreateContainer("dbs/" + database['id'], container_definition, {'offerThroughput': 400})
except errors.HTTPFailure as e:
    if e.status_code == http_constants.StatusCodes.CONFLICT:
        container = client.ReadContainer("dbs/" + database['id'] + "/colls/" + container_definition['id'])
    else:
        raise e
database_id = 'CloudDataBase'
container_id = 'weathercontainer'
container = client.ReadContainer("dbs/" + database_id + "/colls/" + container_id)


class City(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)


def get_weather_data(city):
    url = 'http://api.openweathermap.org/data/2.5/weather?q={}&units=metric&lang=en&appid=bcc7a121c2346aae80c03f6b9db0a4d3'.format(city)
    r = requests.get(url).json()
    for i in range(1, 10):
        pass
    client.UpsertItem("dbs/" + database_id + "/colls/" + container_id, {
        'city':city,
    }
                      )
    return r


@app.route('/')
def index_get():
    cities = City.query.all()

    weather_data = []

    for city in cities:

        r = get_weather_data(city.name)
        print(r)

        weather = {
            'city': city.name.title(),
            'temperature': r['main']['temp'],
            'country': r['sys']['country'],
            'description': r['weather'][0]['description'],
            'count': r['main']['humidity'],
            'icon': r['weather'][0]['icon'],
        }

        weather_data.append(weather)

    return render_template('weather.html', weather_data=reversed(weather_data))


@app.route('/', methods=['POST'])
def index_post():
    err_msg = ''
    new_city = request.form.get('city')
    #print("start")
    if new_city:
        existing_city = City.query.filter_by(name=new_city).first()
        #print("start 1")
        if not existing_city:
            new_city_data = get_weather_data(new_city)
            #print("NOT Existing")

            if new_city_data['cod'] == 200:
                new_city_obj = City(name=new_city.lower())

                db.session.add(new_city_obj)
                #print(new_city_obj)
                #print("After lower operation" + new_city)
                #print("Update Name" + new_city_obj.name)
                #print("end")
                db.session.commit()
            else:
                err_msg = 'City does not exist, Please type a correct city!'
        else:
            err_msg = 'City already exists in the database!'

    if err_msg:
        flash(err_msg, 'error')
    else:
        flash('City added successfully!')

    return redirect(url_for('index_get'))


@app.route('/delete/<name>')
def delete_city(name):
    city = City.query.filter_by(name=name.lower()).first()
    print(city)
    db.session.delete(city)
    db.session.commit()

    flash('Successfully deleted {}'.format(city.name), 'success')
    return redirect(url_for('index_get'))