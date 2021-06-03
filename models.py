from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow

db = SQLAlchemy()
ma = Marshmallow()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    review = db.relationship('Feedback', backref='user_detail')

class Places(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    location = db.Column(db.String(100))
    category = db.Column(db.String(50))
    latt = db.Column(db.Float)
    long = db.Column(db.Float)
    description = db.Column(db.String(1000))
    rating = db.Column(db.Float)
    open_link = db.Column(db.String(255))
    review = db.relationship('Feedback', backref='place_detail')

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    place_id = db.Column(db.Integer, db.ForeignKey('places.id'))
    url = db.Column(db.String(500), unique=True)
    content_description = db.Column(db.String(255))
    place_name = db.relationship('Places', backref='image_path')

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    place_id = db.Column(db.Integer, db.ForeignKey('places.id'))
    rating = db.Column(db.Float)
    desc = db.Column(db.String(255))
    date = db.Column(db.Date)
    user = db.relationship('User', backref='reviewer')

class UserSchema(ma.Schema):
    class Meta:
        fields = ('id', 'username')

class Wishlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    place_id = db.Column(db.Integer, db.ForeignKey('places.id'))
    place_detail = db.relationship('Places', backref='place_detail')

class PlacesDetail(ma.Schema):
    class Meta:
        fields = ('id', 'name', 'location', 'lat', 'lng', 'description', 'open_link', 'rating')

class FeedbackSchema(ma.Schema):
    class Meta:
        fields = ('id', 'user_id', 'place_id', 'rating', 'desc', 'date', 'place_detail', 'user_detail')
    
    place_detail = ma.Nested(PlacesDetail, only=("id", "name"))
    user_detail = ma.Nested(UserSchema, exclude=['id'])
        
class ImageSchema(ma.Schema):
    class Meta:
        fields = ('id', 'place_id', 'url', 'content_description')

class PlacesSchema(ma.Schema):
    class Meta:
        fields = ('id', 'name', 'location', 'lat', 'lng', 'description', 'open_link', 'rating', 'image_path', 'link')
    
    image_path = ma.Nested(ImageSchema, many=True, only=("url", "content_description"))
    link = ma.Hyperlinks(
        {
            'self': ma.URLFor('place', values=dict(id="<id>"))
        }
    )

class WishlistSchema(ma.Schema):
    class Meta:
        fields = ('id', 'user_id', 'place_id', 'place_detail', 'link')
        
    place_detail = ma.Nested(PlacesSchema, only=("id", "name", "image_path"))
    link = ma.Hyperlinks(
        {
            'self': ma.URLFor('place', values=dict(id="<place_id>"))
        }
    )