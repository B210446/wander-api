from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow

db = SQLAlchemy()
ma = Marshmallow()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    display_name = db.Column(db.String(150))
    review = db.relationship('Feedback', backref='user_detail')

class Places(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    location = db.Column(db.String(100))
    category = db.Column(db.String(100))
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    description = db.Column(db.String(255))
    rating = db.Column(db.Float)
    external_urls = db.Column(db.String(255))
    review = db.relationship('Feedback', backref='place_detail')

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    place_id = db.Column(db.Integer, db.ForeignKey('places.id'))
    image_path = db.Column(db.String(255), unique=True)
    content_description = db.Column(db.String(255))
    place_name = db.relationship('Places', backref='image_url')

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    place_id = db.Column(db.Integer, db.ForeignKey('places.id'))
    rating = db.Column(db.Float)
    desc = db.Column(db.String(255))
    date = db.Column(db.Date)
    name = db.relationship('Places', backref='reviews')
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
        fields = ('id', 'name', 'location', 'lat', 'long', 'description', 'image_path', 'links')

class FeedbackSchema(ma.Schema):
    class Meta:
        fields = ('id', 'user_id', 'place_id', 'rating', 'desc', 'date', 'place_detail', 'user_detail')
    
    place_detail = ma.Nested(PlacesDetail, only=("id", "name"))
    user_detail = ma.Nested(UserSchema)
        
class WishlistSchema(ma.Schema):
    class Meta:
        fields = ('id', 'user_id', 'place_id', 'place_detail', 'links')
    
    place_detail = ma.Nested(PlacesDetail, only=("id", "name", "image_path"))
    links = ma.Hyperlinks(
        {
            'next': ma.URLFor('place', values=dict(id="<place_id>"))
        }
    )

class ImageSchema(ma.Schema):
    class Meta:
        fields = ('id', 'place_id', 'image_path', 'content_description')

class PlacesSchema(ma.Schema):
    class Meta:
        fields = ('id', 'name', 'location', 'lat', 'lng', 'description', 'image_path', 'image_url', 'reviews', 'links')
    
    image_url = ma.Nested(ImageSchema, many=True, only=("image_path", "content_description"))
    reviews = ma.Nested(FeedbackSchema, many=True, exclude=['place_id', 'user_id',])
    links = ma.Hyperlinks(
        {
            'next': ma.URLFor('place', values=dict(id="<id>"))
        }
    )