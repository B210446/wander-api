from flask_sqlalchemy import SQLAlchemy
import requests
from sqlalchemy.sql.expression import func, null

db = SQLAlchemy()

API_KEY = "AIzaSyDBmn1-rBVvIQU6gKIDpvqfCRJut_uVgeA"

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    review = db.relationship('Feedback', backref='user_detail')

class Wishlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    place_id = db.Column(db.String(30))
    place_name = db.Column(db.String(100))

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    place_id = db.Column(db.String(30))
    rating = db.Column(db.Float)
    desc = db.Column(db.String(255))
    date = db.Column(db.Date)

def mappingPlaces(resp: dict):
    places = []

    for place in resp["results"]:

        if "photos" not in place:
            continue

        poster = {
            "url": "https://maps.googleapis.com/maps/api/place/photo?key="+API_KEY+"&maxwidth=800&photoreference="+place["photos"][0]["photo_reference"],
            "content_description": place["name"]
        }

        location = None
        if "vicinity" in place:
            location = place["vicinity"]

        if "formatted_address" in place:
            location = place["formatted_address"]

        wander_rating = db.session.query(func.avg(Feedback.rating).label('rating')).filter(Feedback.place_id==place["place_id"]).scalar()

        if wander_rating is None:
            rating = place["rating"]
        else:
            rating = (wander_rating+place["rating"])/2

        data = {
        "id": place["place_id"],
        "name": place["name"],
        "poster": poster,
        "location": location,
        "lat": place["geometry"]["location"]["lat"],
        "lng": place["geometry"]["location"]["lng"],
        "is_favorite":  False,
        "rating": rating,
        "open_link": 'http://localhost:5000/api/v1/place?id=' + place["place_id"]
        }

        places.append(data)
    
    return places

def mappingPlace(resp: dict,user):
    place = resp["result"]

    photos = []
    reviews = []

    for photo in place["photos"]:
        image = {
        "url": "https://maps.googleapis.com/maps/api/place/photo?key="+API_KEY+"&maxwidth=800&photoreference="+photo["photo_reference"],
        "content_description": place["name"]
        }
        photos.append(image)

    wander_review = Feedback.query.filter_by(place_id=place["place_id"]).all()

    for item in wander_review:
        name_query = User.query.filter_by(id=wander_review[0].user_id).first()
        review = {
        "username": name_query.username,
        "place_id": item.place_id,
        "rating": item.rating,
        "desc": item.desc,
        "date": item.date
        }
        reviews.append(review)
    
    for item in place["reviews"]:
        review = {
        "username": item["author_name"],
        "place_id": place["place_id"],
        "rating": item["rating"],
        "desc": item["text"],
        "date": item["time"],
        }
        reviews.append(review)


    wiki = getDescriptionFromWiki(place["name"])

    desc = ""
    for item in wiki["query"]["pages"]:

        if "extract" in wiki["query"]["pages"][item]:
            desc = wiki["query"]["pages"][item]["extract"]

    fav = Wishlist.query.filter_by(user_id=user.id, place_id=place["place_id"]).all()

    if fav is None:
        fav = False
    else:
        fav = True

    wander_rating = db.session.query(func.avg(Feedback.rating).label('rating')).filter(Feedback.place_id==place["place_id"]).scalar()

    if wander_rating is None:
        rating = place["rating"]
    else:
        rating = (wander_rating+place["rating"])/2

    if place["website"] is None:
        website = null
    else:
        website = place["website"]

    data = {
    "id": place["place_id"],
    "name": place["name"],
    "image_path": photos,
    "location": place["vicinity"],
    "lat": place["geometry"]["location"]["lat"],
    "lng": place["geometry"]["location"]["lng"],
    "description": desc,
    "open_link": website,
    "add_to_favorite": 'http://localhost:5000/api/v1/wishlist/add?id=' + place["place_id"],
    "review_link": "http://localhost:5000/api/v1/place/review?id=" + place["place_id"],
    "is_favorite":  fav,
    "rating": rating,
    "top_reviews": reviews    
    }

    return data

def mappingWishlist(resp: dict):
    place = resp["result"]

    poster = {
        "url": "https://maps.googleapis.com/maps/api/place/photo?key="+API_KEY+"&maxwidth=800&photoreference="+place["photos"][0]["photo_reference"],
        "content_description": place["name"]
    }

    data = {
    "id": place["place_id"],
    "name": place["name"],
    "image_path": poster,
    "is_favorite":  True,
    "delete_favorite": 'http://localhost:5000/api/v1/wishlist/add?id=' + place["place_id"],
    "open_link": 'http://localhost:5000/api/v1/place?id=' + place["place_id"],
    "rating": place["rating"]
    }

    return data

def mappingUserReview(items):

    name_query = User.query.filter_by(id=items.user_id).first()
   
    data = {
        "id": items.place_id,
        "name": items.place_name,
        "username": name_query.username,
        "rating": items.rating,
        "desc": items.desc,
        "open_link": 'http://localhost:5000/api/v1/place?id=' + items.place_id
    }

    return data

def mappingPlaceReview(resp: dict, wander_review):
    place = resp["result"]
    wander_review = Feedback.query.filter_by(place_id=place["place_id"]).all()

    reviews = []

    i = 0
    for item in wander_review:
        name_query = User.query.filter_by(id=wander_review[i].user_id).first()
                
        review = {
        "username": name_query.username,
        "name": wander_review[i].place_name,
        "rating": wander_review[i].rating,
        "desc": wander_review[i].desc,
        "date": wander_review[i].date
        }
        reviews.append(review)
        i += 1

    for item in place["reviews"]: 
        review = {
        "username": item["author_name"],
        "name": place["name"],
        "rating": item["rating"],
        "desc": item["text"],
        "date": item["time"],
        }
        reviews.append(review)

    return reviews

def getDescriptionFromWiki(title: str):
    query = {
        "action": "query",
        "format": "json",
        "prop": "extracts",
        "exintro": None,
        "explaintext": None,
        "redirects": 1,
        "titles": title
    }

    req = requests.get("https://en.wikipedia.org/w/api.php", params=query)
    resp = req.json()

    return resp
