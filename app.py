from flask import Flask, jsonify, request
from models import db, ma, User, Places, Wishlist, Feedback, PlacesSchema, WishlistSchema, FeedbackSchema
from datetime import date
import jwt
from functools import wraps

app = Flask(__name__)

ENV = 'dev'

if ENV == 'dev':
    app.debug = True
    app.config['SQLALCHEMY_DATABASE_URI'] = '[LOCAL_DATABASE_URL]'
else:
    app.debug = False
    app.config['SQLALCHEMY_DATABASE_URI'] = '[PRODUCTION_DATABASE_URL]'

app.config['SECRET_KEY'] = 'thisissecretkey'
app.config['JSON_SORT_KEYS'] = False
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
ma.init_app(app)

# 
# with app.app_context():
#     db.create_all()

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'api-token' in request.headers:
            token = request.headers['api-token']

        if not token:
            return jsonify({'status' : 401, 'message' : 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'])
            current_user = User.query.filter_by(username=data['username']).first()

        except:
            return jsonify({'status' : 401, 'message' : 'Token is invalid!'}), 401

        return f(current_user, *args, **kwargs)

    return decorated

@app.route('/', methods=['GET'])
def homepage():
    return 'Wander API'

@app.route('/user', methods=['POST'])
def create_user():
    user = request.args.get('user')
    name = request.args.get('display_name')
    token = jwt.encode({'username' : user}, app.config['SECRET_KEY'])

    new_user = User(username=user, display_name=name)
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({
        'message' : 'New user created!',
        'token' : token.decode('UTF-8')
    })

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

@app.route('/place/<int:id>', methods=['GET'])
@token_required
def place(current_user, id):
    place_schema = PlacesSchema(exclude=['image_path', 'links'])
    result = Places.query.get(id)
    response = place_schema.dump(result)
    if db.session.query(Wishlist).filter_by(user_id=current_user.id, place_id=id).all() == []:
        check = False
    else:
        check = True
    return jsonify({
        'status': 200,
        'message': 'OK',
        'data': response,
        'links' : [{
            'review_links' : '/place/' + str(id) + '/feedback',
            'create_review_links' : '/place/' + str(id) + '/feedback/create',
            'add_to_wishlist' : '/place/' + str(id) + '/wishlist/add',
            'is_wishlist' : check
        }]
    })

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

@app.route('/place/<int:place_id>/wishlist/add', methods=['POST'])
@token_required
def add_wishlist(current_user, place_id):
    new_wishlist_schema = WishlistSchema(only=('user_id', 'place_id'))
    check = db.session.query(Wishlist).filter_by(user_id=current_user.id, place_id=place_id).all()
    if  check == []:
        new_wishlist = Wishlist(user_id=current_user.id, place_id=place_id)
        db.session.add(new_wishlist)
        db.session.commit()
        response = new_wishlist_schema.dump(new_wishlist)
        return jsonify({
            'status': 200,
            'message': 'OK',
            'data': response
        })
    else:
        delete = db.session.query(Wishlist).filter_by(user_id=current_user.id, place_id=place_id).first()
        db.session.delete(delete)
        db.session.commit()
        return jsonify({
            'status': 200,
            'message': 'Delete Success'
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
    search = "%{}%".format(query)
    result = Places.query.filter(Places.name.ilike(search)).all()
    response = home_schema.dump(result)
    return jsonify({
        'status': 200,
        'message': 'OK',
        'data': response
    })

if __name__ == '__main__':
    app.run()