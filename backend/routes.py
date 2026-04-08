from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################
@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "OK"})

@app.route('/count', methods=['GET'])
def count():
    """Endpoint to get the count of songs in the database."""
    count = db.songs.count_documents({})
    return jsonify({"count": count})

@app.route('/song', methods=['GET'])
def songs():
    """Endpoint to get all songs in the database."""
    songs = list(db.songs.find({}))
    return json_util.dumps(songs), 200

@app.route('/song/<int:id>', methods=['GET'])
def get_song_by_id(id):
    song = db.songs.find_one({"id":id})
    if not song:
        return {"message": "song with id: %s not found" % id}, 404
    return json_util.dumps(song), 200

@app.route('/song', methods=['POST'])
def create_song():
    data = request.get_json()
    if not data:
        return {"message": "No data provided"}, 400
    if db.songs.find_one({"id": data.get("id")}):
        return {"message": "song with id: %s already present" % data.get("id")}, 302
    result: InsertOneResult = db.songs.insert_one(data)
    if result.acknowledged:
        return {"message": "song created successfully"}, 201
    else:
        return {"message": "Failed to create song"}, 500
    
@app.route('/song/<int:id>', methods=['PUT'])
def update_song(id):
    data = request.get_json()
    if not data:
        return {"message": "No data provided"}, 400
    to_update = db.songs.find_one({"id":id})
    if not to_update:
        return {"message":"song not found"}, 404
    result = db.songs.update_one({"id":id}, {"$set": data})
    if result.modified_count == 0:
        return {"message": "song found, but nothing updated"}, 200
    if result.acknowledged:
        return json_util.dumps(db.songs.find_one({"id":id})), 201
    
@app.route('/song/<int:id>', methods=['DELETE'])
def delete_song(id):
    result = db.songs.delete_one({"id":id})
    if result.deleted_count == 0:
        return {"message": "song not found"}, 404
    if result.deleted_count == 1:
        return {}, 204