from flask import Flask, request
import requests
from models import db, User, Wishlist, Feedback, mappingPlaces, mappingPlace, mappingWishlist, mappingUserReview, mappingPlaceReview
from datetime import date
import jwt
import os
import numpy as np
import tensorflow as tf
from tensorflow import keras
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.config['JSON_SORT_KEYS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:123456@localhost/places'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'thisissecretkey'

API_KEY = "AIzaSyDBmn1-rBVvIQU6gKIDpvqfCRJut_uVgeA"

db.init_app(app)

# with app.app_context():
#     db.create_all()

model_path = "./saved_model"
model = tf.keras.models.load_model(model_path)
class_names = ['Allianz Ecopark', 'Ancol', 'Galangan Kapal Voc', 'Hutan Kota Srengseng', 'Hutan Kota Tanah Tingal', 'Jembatan Gantung Kota Intan', 'Jimbaran Outdoor Lounge', 'Kepulauan Seribu', 'Monumen Nasional', 'Museum Bahari', 'Museum Bank Indonesia', 'Museum Bank Mandiri', 'Museum Fatahillah', 'Museum Joang 45', 'Museum Nasional', 'Museum Naskah Proklamasi', 'Museum Satria Mandala', 'Museum Seni Rupa Dan Keramik', 'Museum Taman Prasasti', 'Museum Tekstil', 'Museum Tengah Kebun', 'Museum Wayang', 'Pelabuhan Sunda Kelapa', 'Setu Babakan', 'Studio Alam Tvri', 'Syahbandar Tower', 'Taman Cattleya', 'Taman Marga Satwa Ragunan', 'Taman Mini Indonesia Indah', 'Taman Suropati', 'Tribeca Park', 'Twin House']

@app.route('/', methods=['GET'])
def homepage():
    return {
        'status': 'success',
        'message': 'Wander API',
        'code': 200
    }

@app.route('/api/v1/user/create', methods=['POST'])
def create_user():
    user = request.args.get('user')
    token = jwt.encode({'username' : user}, app.config['SECRET_KEY'])

    new_user = User(username=user)
    db.session.add(new_user)
    db.session.commit()
    
    return {
        'message' : 'New user created!',
        'key' : token.decode('UTF-8')
    }

@app.route("/api/v1/home")
def home():
    query = {
        "region": "id",
        "query": "wisata jakarta",
        "type": "tourist_attraction",
        "key": API_KEY
    }

    req = requests.get("https://maps.googleapis.com/maps/api/place/textsearch/json", params=query)
    resp = req.json()

    if (resp["status"] == "OK"):

        data = mappingPlaces(resp)
        next_page_token = None
        
        if "next_page_token" in resp:
            next_page_token = resp["next_page_token"]

        return {
        "status": "success",
        "message": "Successfully fetch data",
        "code": 201,
        "data": data,
        "links": {
            "next_page_token": next_page_token
        }
        }
    else:
        return {
        "status": "failure",
        "message": "Request Failed",
        "code": 422,
        "data": None,
        "links": {
            "next_page_token": None
        }
        }

@app.route("/api/v1/search", methods=['GET', 'POST'])
def places_search():
    if request.method == 'GET':
        q = request.args.get('q')
        query = {
            "region": "id",
            "query": q,
            "type": "tourist_attraction",
            "key": API_KEY
        }
        req = requests.get("https://maps.googleapis.com/maps/api/place/textsearch/json", params=query)
        resp = req.json()
        
        if (resp["status"] == "OK"):

            data = mappingPlaces(resp)
            next_page_token = None

            if "next_page_token" in resp:
                next_page_token = resp["next_page_token"]

            return {
            "status": "success",
            "message": "Successfully fetch data",
            "code": 201,
            "data": data,
            "links": {
                "next_page_token": next_page_token
                }
            }
        else:
            return {
            "status": "failure",
            "message": "Request Failed",
            "code": 422,
            "data": None,
            "links": {
                "next_page_token": None
                }
            }
    else:
        image = request.files["image"]

        basepath = os.path.dirname(__file__)
        file_path = os.path.join(basepath, 'uploads', secure_filename(image.filename))
        image.save(file_path)

        img = keras.preprocessing.image.load_img(file_path, target_size=(100, 100))
        img_array = keras.preprocessing.image.img_to_array(img)
        img_array = tf.expand_dims(img_array, 0)

        predictions = model.predict(img_array)
        score = tf.nn.softmax(predictions[0])
        
        query = {
            "region": "id",
            "query": class_names[np.argmax(score)],
            "type": "tourist_attraction",
            "key": API_KEY
        }

        req = requests.get("https://maps.googleapis.com/maps/api/place/textsearch/json", params=query)
        resp = req.json()
        
        data = mappingPlaces(resp)
        next_page_token = None

        if "next_page_token" in resp:
            next_page_token = resp["next_page_token"]

        return {
            "status": "success",
            "message": "Successfully fetch data",
            "code": 201,
            "data": data,
            "links": {
                "next_page_token": next_page_token
                }
            }

@app.route("/api/v1/place", methods=['GET'])
def get_google_place():
    key = request.args.get('key')
    data = jwt.decode(key, app.config['SECRET_KEY'])
    user = User.query.filter_by(username=data['username']).first()
    
    place_id = request.args.get('id')
    query = {
        "place_id": place_id,
        "key": API_KEY
    }

    req = requests.get("https://maps.googleapis.com/maps/api/place/details/json", params=query)
    resp = req.json()

    if (resp["status"] == "OK"):

        data = mappingPlace(resp, user)
        return {
        "status": "success",
        "message": "Successfully fetch data",
        "code": 201,
        "data": data,
        "links": {
            "self": None,
            "next": None,
            "prev": None,
            }
        }
    else:
        return {
        "status": "failure",
        "message": "Request Failed",
        "code": 422,
        "data": None,
        "links": {
            "self": None,
            "next": None,
            "prev": None
            }
        }

@app.route('/api/v1/wishlist/add', methods=['POST'])
def add_wishlist():
    key = request.args.get('key')
    data = jwt.decode(key, app.config['SECRET_KEY'])
    user = User.query.filter_by(username=data['username']).first()

    id = request.args.get('id')

    query = {
        "place_id": id,
        "key": API_KEY
    }

    req = requests.get("https://maps.googleapis.com/maps/api/place/details/json", params=query)
    resp = req.json()

    name = resp["result"]["name"]

    check = db.session.query(Wishlist).filter_by(user_id=user.id, place_id=id).all()
    
    if  check == []:
        new_wishlist = Wishlist(user_id=user.id, place_id=id, place_name=name)
        db.session.add(new_wishlist)
        db.session.commit()
        return {
            'status': 'success',
            'message': 'Successfully Added',
            'code': 201
        }
    else:
        delete = db.session.query(Wishlist).filter_by(user_id=user.id, place_id=id).first()
        db.session.delete(delete)
        db.session.commit()

        return {
            'status': 'success',
            'message': 'Successfully Deleted',
            'code': 200
        }

@app.route('/api/v1/wishlist', methods=['GET'])
def wishlist():
    key = request.args.get('key')
    data = jwt.decode(key, app.config['SECRET_KEY'])
    
    user = User.query.filter_by(username=data['username']).first()

    result = Wishlist.query.filter_by(user_id=user.id).all()

    response = []

    for items in result:
            query = {
                "place_id": items.place_id,
                "key": API_KEY
            }
            req = requests.get("https://maps.googleapis.com/maps/api/place/details/json", params=query)
            resp = req.json()

            response.append(mappingWishlist(resp))
    
    return {
        'status': 'success',
        'message': 'Successfully fetched',
        'code': 200,
        'data': response
        # 'links': pagination
    }

@app.route('/api/v1/place/review/create', methods=['POST'])
def create_feedback():
    key = request.args.get('key')
    if key is None:
        return {
            "status": "failure",
            "message": "Token Not Found",
            "code": 400,
        }
    data = jwt.decode(key, app.config['SECRET_KEY'])
    
    id = request.args.get('id')
    user = User.query.filter_by(username=data['username']).first()

    query = {
        "place_id": id,
        "key": API_KEY
    }

    req = requests.get("https://maps.googleapis.com/maps/api/place/details/json", params=query)
    resp = req.json()

    name = resp["result"]["name"]

    check = db.session.query(Feedback).filter_by(user_id=user.id, place_id=id).all()

    if  check == []:
        rate = request.args.get('rate')
        desc = request.args.get('desc')
        hari = date.today()
        new_feedback = Feedback(user_id=user.id, place_id=id, rating=rate, desc=desc, date=hari, place_name=name)
        db.session.add(new_feedback)
        db.session.commit()

        return {
            'status': 'success',
            'message': 'Successfully added',
            'code': 201
            # 'data': response
        }
    else:        
        return {
            'status': 'User already has review',
            'message': 'Not added',
            'code': 200
        }

@app.route('/api/v1/review', methods=['GET'])
def feedback():
    key = request.args.get('key')
    data = jwt.decode(key, app.config['SECRET_KEY'])
    user = User.query.filter_by(username=data['username']).first()

    result = Feedback.query.filter_by(user_id=user.id).all()

    response = []

    for items in result:
        response.append(mappingUserReview(items))

    return {
        'status': 'success',
        'message': 'Successfully fetched',
        'code': 200,
        'data': response
        # 'links': pagination
    }

@app.route('/api/v1/place/review', methods=['GET'])
def get_feedback():
    place_id = request.args.get('id')
    query = {
        "place_id": place_id,
        "key": API_KEY
    }

    req = requests.get("https://maps.googleapis.com/maps/api/place/details/json", params=query)
    resp = req.json()

    if (resp["status"] == "OK"):
        data = mappingPlaceReview(resp)
        return {
        "status": "success",
        "message": "Successfully fetch data",
        "code": 201,
        "data": data,
        "links": {
            "self": None,
            "next": None,
            "prev": None,
            }
        }
    else:
        return {
        "status": "failure",
        "message": "Request Failed",
        "code": 422,
        "data": None,
        "links": {
            "self": None,
            "next": None,
            "prev": None
            }
        }

if __name__ == '__main__':
    app.run()