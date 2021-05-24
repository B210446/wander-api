from flask import Flask, jsonify, request, make_response
from models import db, ma, User, Places, Wishlist, Feedback, PlacesSchema, WishlistSchema, FeedbackSchema
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
from datetime import date
import jwt
from functools import wraps

app = Flask(__name__)

ENV = 'prod'

if ENV == 'dev':
    app.debug = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:123456@localhost/wander'
else:
    app.debug = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://bjrmmwelqaihwc:cd06dd6ba32aa9e4f3fe4a331ae9cb7cdf34a98acc99d857ae4654c16097ddd7@ec2-52-4-111-46.compute-1.amazonaws.com:5432/d8k78r4r8ckhgp'

app.config['SECRET_KEY'] = 'thisissecretkey'
app.config['JSON_SORT_KEYS'] = False
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
ma.init_app(app)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'api-token' in request.headers:
            token = request.headers['api-token']

        if not token:
            return jsonify({
                'status' : 401,
                'message' : 'Token is missing!'
                }), 401

        try: 
            data = jwt.decode(token, app.config['SECRET_KEY'])
            current_user = User.query.filter_by(id=data['id']).first()
        except:
            return jsonify({
                'status' : 401,
                'message' : 'Token is invalid!'
                }), 401

        return f(current_user, *args, **kwargs)

    return decorated

@app.route('/', methods=['GET'])
def homepage():
    return 'Wander API'

@app.route('/home', methods=['GET'])
def home():
    home_schema = PlacesSchema(many=True, only=("id", "name", "image_path", 'links'))
    result = Places.query.all()
    response = home_schema.dump(result)
    return jsonify({
        'status': 200,
        'message': 'OK',
        'data': response
    })

@app.route('/login')
def login():
    auth = request.authorization

    if not auth or not auth.username or not auth.password:
        return make_response('Could not verify', 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'})

    user = User.query.filter_by(username=auth.username).first()

    if not user:
        return make_response('Could not verify', 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'})

    if check_password_hash(user.password, auth.password):
        token = jwt.encode({'id' : user.id, 'exp' : datetime.datetime.utcnow() + datetime.timedelta(minutes=30)}, app.config['SECRET_KEY'])

        return jsonify({'token' : token.decode('UTF-8')})

    return make_response('Could not verify', 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'})

@app.route('/wishlist')
@token_required
def wishlist(current_user):
    wishlist_schema = WishlistSchema(many=True, only=('id', 'place_detail', 'links'))
    result = Wishlist.query.filter_by(user_id=current_user.id).all()
    response = wishlist_schema.dump(result)
    return jsonify({
        'status': 200,
        'message': 'OK',
        'data': response
    })

@app.route('/feedback', methods=['GET'])
@token_required
def feedback(current_user):
    feedback_schema = FeedbackSchema(many=True, exclude=['user_detail', 'user_id', 'place_id'])
    result = Feedback.query.filter_by(user_id=current_user.id).all()
    response = feedback_schema.dump(result)
    return jsonify({
        'status': 200,
        'message': 'OK',
        'data': response
    })

@app.route('/place/<int:id>', methods=['GET'])
def place(id):
    place_schema = PlacesSchema(exclude=['image_path', 'links'])
    result = Places.query.get(id)
    response = place_schema.dump(result)
    return jsonify({
        'status': 200,
        'message': 'OK',
        'data': response
    })

@app.route('/place/<int:id>/feedback', methods=['GET'])
def get_feedback(id):
    feedback_schema = FeedbackSchema(many=True, exclude=['user_id', 'place_id', 'place_detail'])
    result = Feedback.query.filter_by(place_id=id).all()
    response = feedback_schema.dump(result)
    return jsonify({
        'status': 200,
        'message': 'OK',
        'data': response
    })

@app.route('/place/<int:place_id>/feedback/create', methods=['POST'])
@token_required
def create_feedback(current_user, place_id):
    feedback_schema = FeedbackSchema()
    check = db.session.query(Feedback).filter_by(user_id=current_user.id, place_id=place_id).all()
    if  check == []:
        rate = request.args.get('rate')
        desc = request.args.get('desc')
        hari = date.today()
        new_feedback = Feedback(user_id=current_user.id, place_id=place_id, rating=rate, desc=desc, date=hari)
        db.session.add(new_feedback)
        db.session.commit()
        response = feedback_schema.dump(new_feedback)
        return jsonify({
            'status': 200,
            'message': 'OK',
            'data': response
        })
    else:
        print(check)
        return 'Sudah ada feedback dari user ini', 200

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q')
    home_schema = PlacesSchema(many=True, only=("id", "name", "image_path", 'links'))
    result = Places.query.filter_by(name=query).all()
    response = home_schema.dump(result)
    return jsonify({
        'status': 200,
        'message': 'OK',
        'data': response
    })

@app.route('/user', methods=['POST'])
def create_user():
    user = request.args.get('user')
    pw = request.args.get('password')
    name = request.args.get('display_name')

    hashed_password = generate_password_hash(pw, method='sha256')

    new_user = User(username=user, password=hashed_password, display_name=name)
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({'message' : 'New user created!'})

if __name__ == '__main__':
    app.run()