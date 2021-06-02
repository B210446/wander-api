from flask import Flask, jsonify, request
from models import db, ma, User, Places, Wishlist, Feedback, PlacesSchema, WishlistSchema, FeedbackSchema
import tensorflow as tf
from tensorflow import keras
from sqlalchemy.sql import func
from datetime import date
import jwt
import os
import numpy as np
from werkzeug.utils import secure_filename

app = Flask(__name__)

ENV = 'prod'

if ENV == 'dev':
    app.debug = True
    app.config['SQLALCHEMY_DATABASE_URI'] = '[LOCAL DATABASE URL]'
else:
    app.debug = False
    app.config['SQLALCHEMY_DATABASE_URI'] = '[PRODUCTION DATABASE URL]'

app.config['SECRET_KEY'] = '[SECRET KEY]'
app.config['JSON_SORT_KEYS'] = False
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
ma.init_app(app)

# with app.app_context():
#     db.create_all()

model_path = "[MODEL PATH]"
model = tf.keras.models.load_model(model_path)
class_names = ['Allianz Ecopark', 'Ancol', 'Galangan Kapal Voc', 'Hutan Kota Srengseng', 'Hutan Kota Tanah Tingal', 'Jembatan Gantung Kota Intan', 'Jimbaran Outdoor Lounge', 'Kepulauan Seribu', 'Monumen Nasional', 'Museum Bahari', 'Museum Bank Indonesia', 'Museum Bank Mandiri', 'Museum Fatahillah', 'Museum Joang 45', 'Museum Nasional', 'Museum Naskah Proklamasi', 'Museum Satria Mandala', 'Museum Seni Rupa Dan Keramik', 'Museum Taman Prasasti', 'Museum Tekstil', 'Museum Tengah Kebun', 'Museum Wayang', 'Pelabuhan Sunda Kelapa', 'Setu Babakan', 'Studio Alam Tvri', 'Syahbandar Tower', 'Taman Cattleya', 'Taman Marga Satwa Ragunan', 'Taman Mini Indonesia Indah', 'Taman Suropati', 'Tribeca Park', 'Twin House']

@app.route('/', methods=['GET'])
def homepage():
    return jsonify({
        'status': 'success',
        'message': 'Wander API',
        'code': 200
    })

@app.route('/user', methods=['POST'])
def create_user():
    user = request.args.get('user')
    token = jwt.encode({'username' : user}, app.config['SECRET_KEY'])

    new_user = User(username=user)
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({
        'message' : 'New user created!',
        'key' : token.decode('UTF-8')
    })

@app.route('/api/v1/search', methods=['GET'])
def search():
    page = request.args.get("page")
    image = request.files["images"] 

    if page is None:
        page = 1

    next = int(page)+1
    prev = int(page)-1

    home_schema = PlacesSchema(many=True, only=("id", "name", 'link'))

    if image is not None:
        basepath = os.path.dirname(__file__)
        basepath = os.path.dirname(__file__)
        file_path = os.path.join(basepath, 'uploads', secure_filename(image.filename))
        image.save(file_path)
        
        img = keras.preprocessing.image.load_img(file_path, target_size=(180, 180))
        x = keras.preprocessing.image.img_to_array(img)
        x = tf.expand_dims(x, 0)
        x = x/255.0

        predictions = model.predict(x)
        score = tf.nn.softmax(predictions[0])

        result = Places.query.filter(Places.name.ilike(class_names[np.argmax(score)])).paginate(per_page=15, page=int(page))
        response = home_schema.dump(result)

    else:
        query = request.args.get('q')
        search = "%{}%".format(query)
        result = Places.query.filter(Places.name.ilike(search)).paginate(per_page=15, page=int(page))
        response = home_schema.dump(result)

    pagination = {}
    pagination['self'] = '/api/v1/home?page=' + str(page)
    pagination['next'] = '/api/v1/home?page=' + str(next)

    if prev == 0:
        pagination['prev'] = None
    else:
        pagination['prev'] = '/api/v1/home?page=' + str(prev)

    return jsonify({
        'status': 'success',
        'message': 'Successfully fetched',
        'code': 200,
        'data': response
    })

@app.route('/api/v1/home', methods=['GET'])
def home():
    page = request.args.get("page")

    if page is None:
        page = 1

    next = int(page)+1
    prev = int(page)-1

    home_schema = PlacesSchema(many=True, only=("id", "name", "image_path", 'link'))
    result = Places.query.paginate(per_page=15, page=int(page))
    response = home_schema.dump(result.items)
  
    pagination = {}
    pagination['self'] = '/api/v1/home?page=' + str(page)
    pagination['next'] = '/api/v1/home?page=' + str(next)

    if prev == 0:
        pagination['prev'] = None
    else:
        pagination['prev'] = '/api/v1/home?page=' + str(prev)

    return ({
        'status': 'success',
        'message': 'Successfully fetched',
        'code': 200,
        'data': response,
        'links': pagination
    })

@app.route('/api/v1/place/<int:id>', methods=['GET'])
def place(id):
    key = request.args.get('key')
    data = jwt.decode(key, app.config['SECRET_KEY'])
    user = User.query.filter_by(username=data['username']).first()

    place_schema = PlacesSchema(exclude=['link'])
    result = Places.query.get(id)
    response = place_schema.dump(result)

    feedback_schema = FeedbackSchema(many=True, exclude=['place_id', 'user_id'])
    review = db.session.query(Feedback).filter_by(place_id=id).limit(5)
    top_review = feedback_schema.dump(review) 

    if db.session.query(Wishlist).filter_by(user_id=user.id, place_id=id).all() == []:
        check = False
    else:
        check = True

    response["top_review"] = top_review
    response["is_favorite"] = check
    response["review_link"] = '/api/v1/place/' + str(id) + '/feedback'
    response["create_review_link"] = '/api/v1/place/' + str(id) + '/feedback'
    response["add_to_wishlist"] = '/api/v1/place/' + str(id) + '/wishlist/add'

    return jsonify({
        'status': 'success',
        'message': 'Successfully fetched',
        'code': 200,
        'data': response
    })

@app.route('/api/v1/wishlist')
def wishlist():
    key = request.args.get('key')
    data = jwt.decode(key, app.config['SECRET_KEY'])
    user = User.query.filter_by(username=data['username']).first()

    page = request.args.get("page")

    if page is None:
        page = 1

    next = int(page)+1
    prev = int(page)-1

    wishlist_schema = WishlistSchema(many=True, only=('id', 'place_detail', 'link'))
    result = Wishlist.query.filter_by(user_id=user.id).paginate(per_page=15, page=int(page))
    response = wishlist_schema.dump(result.items)

    pagination = {}
    pagination['self'] = '/api/v1/home?page=' + str(page)
    pagination['next'] = '/api/v1/home?page=' + str(next)

    if prev == 0:
        pagination['prev'] = None
    else:
        pagination['prev'] = '/api/v1/home?page=' + str(prev)

    return jsonify({
        'status': 'success',
        'message': 'Successfully fetched',
        'code': 200,
        'data': response,
        'links': pagination
    })

@app.route('/api/v1/place/<int:place_id>/wishlist/add', methods=['POST'])
def add_wishlist(place_id):
    key = request.args.get('key')
    data = jwt.decode(key, app.config['SECRET_KEY'])
    user = User.query.filter_by(username=data['username']).first()

    new_wishlist_schema = WishlistSchema(only=('user_id', 'place_id'))
    check = db.session.query(Wishlist).filter_by(user_id=user.id, place_id=place_id).all()
    if  check == []:
        new_wishlist = Wishlist(user_id=user.id, place_id=place_id)
        db.session.add(new_wishlist)
        db.session.commit()
        response = new_wishlist_schema.dump(new_wishlist)

        return jsonify({
            'status': 'success',
            'message': 'Successfully fetched',
            'code': 201,
            'data': response
        })
    else:
        delete = db.session.query(Wishlist).filter_by(user_id=user.id, place_id=place_id).first()
        db.session.delete(delete)
        db.session.commit()

        return jsonify({
            'status': 200,
            'message': 'Delete Success'
        })

@app.route('/api/v1/feedback', methods=['GET'])
def feedback():
    key = request.args.get('key')
    data = jwt.decode(key, app.config['SECRET_KEY'])
    user = User.query.filter_by(username=data['username']).first()

    page = request.args.get("page")

    if page is None:
        page = 1

    next = int(page)+1
    prev = int(page)-1

    feedback_schema = FeedbackSchema(many=True, exclude=['user_id', 'place_id'])
    result = Feedback.query.filter_by(user_id=user.id).paginate(per_page=15, page=int(page))
    response = feedback_schema.dump(result)

    pagination = {}
    pagination['self'] = '/api/v1/home?page=' + str(page)
    pagination['next'] = '/api/v1/home?page=' + str(next)

    if prev == 0:
        pagination['prev'] = None
    else:
        pagination['prev'] = '/api/v1/home?page=' + str(prev)

    return jsonify({
        'status': 'success',
        'message': 'Successfully fetched',
        'code': 200,
        'data': response.append,
        'links': pagination
    })

@app.route('/api/v1/place/<int:id>/feedback', methods=['GET'])
def get_feedback(id):
    feedback_schema = FeedbackSchema(many=True, exclude=['user_id', 'place_id', 'place_detail'])
    result = Feedback.query.filter_by(place_id=id).all()
    response = feedback_schema.dump(result)
    
    return jsonify({
        'status': 'success',
        'message': 'Successfully fetched',
        'code': 200,
        'data': response
    })

@app.route('/api/v1/place/<int:place_id>/feedback/create', methods=['POST'])
def create_feedback(place_id):
    key = request.args.get('key')
    data = jwt.decode(key, app.config['SECRET_KEY'])
    user = User.query.filter_by(username=data['username']).first()

    feedback_schema = FeedbackSchema(exclude=['id', 'place_id', 'user_id'])
    check = db.session.query(Feedback).filter_by(user_id=user.id, place_id=place_id).all()

    if  check == []:
        rate = request.args.get('rate')
        desc = request.args.get('desc')
        hari = date.today()
        new_feedback = Feedback(user_id=user.id, place_id=place_id, rating=rate, desc=desc, date=hari)
        db.session.add(new_feedback)
        update_rating = db.session.query(func.avg(Feedback.rating).label('rating')).filter(Feedback.place_id==place_id).scalar()
        db.session.query(Places).filter(Places.id==place_id).update({Places.rating:update_rating})
        db.session.commit()
        response = feedback_schema.dump(new_feedback)

        return jsonify({
            'status': 'success',
            'message': 'Successfully added',
            'code': 201,
            'data': response
        })
    else:        
        return jsonify({
            'status': 'User already has review',
            'message': 'Not added',
            'code': 200
        })

if __name__ == '__main__':
    app.run()