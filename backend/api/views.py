import json
import jwt
import smtplib
import os
import zipfile
import io
import uuid
from bson.json_util import dumps
from django.http.multipartparser import MultiPartParser
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from urllib.parse import urljoin
from mimetypes import guess_extension
from bcrypt import hashpw, gensalt, checkpw
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.http import HttpResponse, JsonResponse, HttpResponseServerError
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from pymongo import MongoClient, errors
from pyinaturalist import get_observations, get_taxa
from bson import ObjectId
import datetime as dt
from bson.errors import InvalidId
from datetime import datetime, timedelta
from django.utils.timezone import now
import requests
from django.shortcuts import redirect
import time
import logging
import traceback
from shapely.geometry import Point, Polygon

# Sets up logging for error tracking
logger = logging.getLogger(__name__)
SECRET = settings.SECRET_KEY

# MongoDB connection
try:
    client = MongoClient(settings.MONGO_DB_URI, serverSelectionTimeoutMS=5000)
    client.server_info()  
    db = client.get_database()
except Exception as e:
    logger.error(f"[MongoDB] Connection failed: {e}")
    db = None

# Define collections we'll be working with
species_collection = db["species"]
locations_collection = db["locations"]
observations_collection = db["observations"]
users_collection = db["users"]
comments_collection = db["comments"]

def admin_required(view_func):
    """
    Decorator to restrict access to admin users only.
    Checks JWT token and verifies admin role before allowing access.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Gets authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return JsonResponse({"error": "Authorization header missing or invalid"}, status=401)
        
        # Extracts and verifies JWT token
        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(token, SECRET, algorithms=["HS256"])
            user_id = payload.get("user_id")
            if not user_id:
                return JsonResponse({"error": "Invalid token payload"}, status=401)

            # Checks if user exists
            user = users_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                return JsonResponse({"error": "User not found"}, status=404)
            
            if user.get("isBlocked", False):
                return JsonResponse({"error": "User account is blocked"}, status=403)
            
            # Verifies admin role
            if "admin" not in user.get("roles", []):
                return JsonResponse({"error": "Admin access required"}, status=403)
            
            # Attaches user info to request for use in view
            request.user_info = user
            return view_func(request, *args, **kwargs)

        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, InvalidId):
            return JsonResponse({"error": "Invalid or expired token"}, status=401)
        except Exception as e:
            logger.error(f"Error in admin_required decorator: {e}")
            return JsonResponse({"error": "An internal server error occurred"}, status=500)
    return _wrapped_view

def user_required(view_func):
    """
    Decorator to ensure user is authenticated.
    Validates JWT token and attaches user info to request.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return JsonResponse({"error": "Authorization header missing or invalid"}, status=401)

        # Extracts and verifies token
        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(token, SECRET, algorithms=["HS256"])
            user_id = payload.get("user_id")
            if not user_id:
                return JsonResponse({"error": "Invalid token payload"}, status=401)

            # Verifies user exists
            user = users_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                return JsonResponse({"error": "User not found"}, status=404)
            
            if user.get("isBlocked", False):
                return JsonResponse({"error": "User account is blocked"}, status=403)

            # Attaches user to request
            request.user_info = user
            return view_func(request, *args, **kwargs)

        except (ExpiredSignatureError, InvalidTokenError):
            return JsonResponse({"error": "Invalid or expired token"}, status=401)
        except Exception as e:
            logger.error(f"Error in user_required decorator: {e}")
            return JsonResponse({"error": "An internal server error occurred"}, status=500)
    return _wrapped_view

# Defines polygon boundaries for each continent for geospatial queries
CONTINENT_POLYGONS = {
    "North America": Polygon([(-170, 5), (-170, 85), (-50, 85), (-50, 5)]),
    "South America": Polygon([(-85, -60), (-85, 15), (-30, 15), (-30, -60)]),
    "Europe": Polygon([(-30, 35), (-30, 72), (60, 72), (60, 35)]),
    "Africa": Polygon([(-20, -40), (-20, 35), (60, 35), (60, -40)]),
    "Asia": Polygon([(30, 0), (30, 80), (180, 80), (180, 0)]),
    "Australia": Polygon([(110, -50), (110, 0), (180, 0), (180, -50)]),
    "Antarctica": Polygon([(-180, -90), (-180, -60), (180, -60), (180, -90)])
}

@csrf_exempt
def register(request):
    """Handles new user registration with email verification."""
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    # Parses registration data
    data = json.loads(request.body)
    email = data.get("email")
    name = data.get("full_name", "")
    username = data.get("username")
    password = data.get("password")

    # Checks for existing email
    if users_collection.find_one({"email": email}):
        return JsonResponse({"error": "Email already in use"}, status=409)

    # Hashes password securely
    hashed_pw = hashpw(password.encode('utf-8'), gensalt())

    # Creates new user document
    user = {
        "email": email,
        "username": username,
        "password": hashed_pw,
        "is_verified": False,
        "name": name,
        "roles": ["user"],
        "created_at": datetime.utcnow()
    }

    # Inserts user and generates verification token
    inserted = users_collection.insert_one(user)
    user_id = str(inserted.inserted_id)

    # Creates verification link with 1-hour expiry
    token = jwt.encode({"user_id": user_id, "exp": datetime.utcnow() + timedelta(hours=1)}, SECRET, algorithm="HS256")
    verify_link = f"http://localhost:8000/api/auth/verify-email/?token={token}"

    try:
        # Sends verification email
        send_email(email, verify_link)
        return JsonResponse({"message": "User registered. Check your email to verify."}, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def send_email(to_email, link, purpose="verify"):
    """
    Sends email for verification or password reset.
    Supports both HTML and plain text content.
    """
    if purpose == "verify":
        subject = "Verify your email"
        body_html = f"""
        <html>
        <body>
            <h2>Welcome to Biodiversity Tracker! 🌿</h2>
            <p>Thank you for signing up. Please verify your email:</p>
            <p><a href="{link}">Verify your account</a></p>
            <p>– Biodiversity Tracker Team</p>
        </body>
        </html>
        """
    else:
        subject = "Reset Your Password"
        body_html = f"""
        <html><body>
        <h2>Reset Your Password 🔑</h2>
        <p>Click the link below to reset your password:</p>
        <a href="{link}">Reset Password</a>
        <p>This link will expire in 15 minutes.</p>
        </body></html>
        """

    # Creates MIME (Multipurpose Internet Mail Extensions) message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_HOST_USER
    msg["To"] = to_email
    msg.attach(MIMEText(body_html, "html"))

    # Connects to SMTP (Simple Mail Transfer Protocol) server and send
    with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=10) as server:
        server.starttls()
        server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        server.sendmail(settings.EMAIL_HOST_USER, [to_email], msg.as_string())


def verify_email(request):
    """Handle email verification link from registration email."""
    token = request.GET.get("token")
    try:
        # Verifies token and marks user as verified
        payload = jwt.decode(token, SECRET, algorithms=["HS256"])
        user_id = payload["user_id"]
        users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": {"is_verified": True}})
        # Redirects to frontend after successful verification
        return redirect("http://localhost:5173/")
    except jwt.ExpiredSignatureError:
        return JsonResponse({"error": "Token expired"}, status=400)
    except Exception:
        return JsonResponse({"error": "Invalid token"}, status=400)

@csrf_exempt
def login(request):
    """Handles user login and returns JWT token."""
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    # Parses login credentials
    data = json.loads(request.body)
    username_or_email = data.get("username_or_email")
    password = data.get("password")

    # Finds user by username or email
    user = users_collection.find_one({"$or": [{"email": username_or_email}, {"username": username_or_email}]})

    # Verifies credentials
    if not user or not checkpw(password.encode('utf-8'), user["password"]):
        return JsonResponse({"error": "Invalid credentials"}, status=401)

    # Checks email verification status
    if not user.get("is_verified", False):
        return JsonResponse({"error": "Email not verified"}, status=403)
    
    # Blocks login if user is blocked
    if user.get("isBlocked", False):
        return JsonResponse({"error": "Account blocked. Contact support for assistance."}, status=403)

    # Generates JWT token
    token = jwt.encode({"user_id": str(user["_id"])}, SECRET, algorithm="HS256")
    
    # Returns user roles and admin status
    user_roles = user.get("roles", ["user"])
    is_admin = "admin" in user_roles
    
    return JsonResponse({
        "token": token,
        "username": user["username"],
        "roles": user_roles,
        "isAdmin": is_admin
    })

@csrf_exempt
def forgot_password(request):
    """
    Handles password reset request.
    Generates reset token and sends email if user exists.
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    # Parses email from request
    data = json.loads(request.body)
    email = data.get("email")

    # Finds user by email
    user = users_collection.find_one({"email": email})
    if not user:
        # Returns generic response to prevent email enumeration
        return JsonResponse({"message": "If the email exists, a reset link has been sent."}, status=200) 

    # Generates reset token with 15 minute expiry
    token = jwt.encode({"user_id": str(user["_id"]), "exp": datetime.utcnow() + timedelta(minutes=15)}, SECRET, algorithm="HS256")
    reset_link = f"http://localhost:5173/auth/reset-password?token={token}"

    try:
        # Sends password reset email
        send_email(email, reset_link, purpose="reset")
        return JsonResponse({"message": "Check your email for the reset link."})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def reset_password(request):
    """
    Handles password reset with new password.
    Validates token and updates password in database.
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    # Parses token and new password from request
    data = json.loads(request.body)
    token = data.get("token")
    new_password = data.get("new_password")

    try:
        # Verifies token and extracts user ID
        payload = jwt.decode(token, SECRET, algorithms=["HS256"])
        user_id = payload["user_id"]
    except jwt.ExpiredSignatureError:
        return JsonResponse({"error": "Reset link expired"}, status=400)
    except Exception:
        return JsonResponse({"error": "Invalid token"}, status=400)

    # Hashes new password before storage
    hashed_pw = hashpw(new_password.encode('utf-8'), gensalt())
    # Updates user password in database
    users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": {"password": hashed_pw}})
    return JsonResponse({"message": "Password updated successfully"})

@require_GET
def get_species_detail(request, species_name):
    """
    Retrieves detailed information about a species including recent observations.
    Returns taxonomy data and geospatial observation information.
    """
    try:
        # Gets species details from database (case-insensitive)
        species = db["species"].find_one({"species": {"$regex": f"^{species_name}$", "$options": "i"}})
        if not species:
            return JsonResponse({"error": "Species not found"}, status=404)
        
        # Build aggregation pipeline for recent observations
        pipeline = [
            {
                "$match": {"species_id": species["_id"]}
            },
            {
                "$lookup": {
                    "from": "locations",
                    "localField": "location_id",
                    "foreignField": "_id",
                    "as": "location"
                }
            },
            {"$unwind": "$location"},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "user_id",
                    "foreignField": "_id",
                    "as": "user"
                }
            },
            {"$unwind": "$user"},
            {
                "$sort": {"timestamp": -1}  # Most recent first
            },
            {
                "$limit": 3  
            },
            {
                "$project": {
                    "_id": 1,
                    "source_id": 1,
                    "timestamp": {
                        "$dateToString": {
                            "format": "%Y-%m-%dT%H:%M:%S.%LZ",
                            "date": "$timestamp"
                        }
                    },
                    "status": 1,
                    "photo": 1,
                    "external_link": 1,
                    "location": {
                        "type": "Point",
                        "coordinates": "$location.geojson.coordinates",
                        "latitude": {"$arrayElemAt": ["$location.geojson.coordinates", 1]},
                        "longitude": {"$arrayElemAt": ["$location.geojson.coordinates", 0]}
                    },
                    "properties": {
                        "species": "$species.species",
                        "genus": "$species.genus",
                        "family": "$species.family",
                        "location_name": "$location.name",
                        "region": "$location.region",
                        "country": "$location.country",
                        "photo": 1,
                        "external_link": 1,
                        "user_name": {
                            "$cond": [
                                {"$or": [
                                    {"$eq": ["$user.name", ""]},
                                    {"$eq": ["$user.name", None]}
                                ]},
                                "$user.username",
                                "$user.name"
                            ]
                        },
                        "user_profile_picture": "$user.profile_picture"
                    }
                }
            }
        ]

        # Executes aggregation pipeline
        observations = list(db["observations"].aggregate(pipeline))

        # Converts BSON to JSON for response
        species_data = convert_bson(species)
        observations_data = convert_bson(observations)

        # Builds absolute URLs for media files
        media_root_url = request.build_absolute_uri(settings.MEDIA_URL)

        # Processes profile picture URLs to ensure absolute paths
        for obs in observations_data:
            pic = obs.get("properties", {}).get("user_profile_picture", "")
            if pic:
                if pic.startswith("http://") or pic.startswith("https://"):
                    profile_picture_url = pic
                elif pic.startswith("/media/"):
                    profile_picture_url = request.build_absolute_uri(pic)
                else:
                    profile_picture_url = urljoin(media_root_url, pic.lstrip("/"))
                obs["properties"]["user_profile_picture"] = profile_picture_url
            else:
                obs["properties"]["user_profile_picture"] = None

        return JsonResponse({
            "species": species_data,
            "recent_observations": observations_data
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@require_GET
def get_species_observations(request, species_name):
    """
    Retrieves all observations for a specific species.
    Returns GeoJSON FeatureCollection of observation locations.
    """
    try:
        # Finds species by exact name match
        species = db["species"].find_one({"species": species_name})
        if not species:
            return JsonResponse({"error": "Species not found"}, status=404)
        
        # Builds aggregation pipeline for species observations
        pipeline = [
            {
                "$match": {"species_id": species["_id"]}
            },
            {
                "$lookup": {
                    "from": "locations",
                    "localField": "location_id",
                    "foreignField": "_id",
                    "as": "location"
                }
            },
            {"$unwind": {"path": "$location", "preserveNullAndEmptyArrays": True}},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "user_id",
                    "foreignField": "_id",
                    "as": "user"
                }
            },
            {"$unwind": {"path": "$user", "preserveNullAndEmptyArrays": True}},
            {
                "$project": {
                    "_id": 0,
                    "source_id": 1,
                    "type": "Feature",
                    "location": {
                        "type": "Point",
                        "coordinates": "$location.geojson.coordinates",
                        "latitude": "$location.latitude",
                        "longitude": "$location.longitude"
                    },
                    "properties": {
                        "species": species["species"],
                        "genus": species.get("genus", ""),
                        "family": species.get("family", ""),
                        "timestamp": {
                            "$cond": {
                                "if": { "$eq": [{ "$type": "$timestamp" }, "date"] },
                                "then": {
                                    "$dateToString": {
                                        "format": "%Y-%m-%dT%H:%M:%S.%LZ",
                                        "date": "$timestamp"
                                    }
                                },
                                "else": "$timestamp"
                            }
                        },
                        "location_name": "$location.name",
                        "region": "$location.region",
                        "country": "$location.country",
                        "status": "$status",
                        "photo": "$photo",
                        "external_link": "$external_link",
                        "user_name": {
                            "$cond": [
                                {"$or": [
                                    {"$eq": ["$user.name", ""]},
                                    {"$eq": ["$user.name", None]}
                                ]},
                                "$user.username",
                                "$user.name"
                            ]
                        },
                        "user_profile_picture": "$user.profile_picture"
                    }
                }
            }
        ]

        # Executes pipeline and process results
        observations = list(db["observations"].aggregate(pipeline))
        observations_data = convert_bson(observations)

        # Builds absolute media URLs
        media_root_url = request.build_absolute_uri(settings.MEDIA_URL)

        # Processes profile picture URLs
        for obs in observations_data:
            pic = obs.get("properties", {}).get("user_profile_picture", "")
            if pic:
                if pic.startswith("http://") or pic.startswith("https://"):
                    profile_picture_url = pic
                elif pic.startswith("/media/"):
                    profile_picture_url = request.build_absolute_uri(pic)
                else:
                    profile_picture_url = urljoin(media_root_url, pic.lstrip("/"))
                obs["properties"]["user_profile_picture"] = profile_picture_url
            else:
                obs["properties"]["user_profile_picture"] = None

        return JsonResponse({
            "type": "FeatureCollection",
            "features": observations_data
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
def get_continent(lat: float, lon: float) -> str:
    """
    Determines continent from latitude/longitude coordinates.
    Uses predefined polygon boundaries for continent detection.
    """
    try:
        point = Point(lon, lat)
        for continent, polygon in CONTINENT_POLYGONS.items():
            if polygon.contains(point):
                return continent
    except Exception as e:
        logger.warning(f"Failed to determine continent: {e}")
    return "Unknown"

@require_GET
def get_continent_options(request):
    """Return list of available continent choices for filtering"""
    return JsonResponse({
        "continents": ["All Continents"] + sorted(CONTINENT_POLYGONS.keys())
    }, safe=False)

@require_GET
def get_genus_by_family(request):
    """Retrieve all genesus belonging to a specified family"""
    family = request.GET.get("family")
    if not family:
        return JsonResponse({"error": "Family not provided"}, status=400)

    genus_list = db["species"].distinct("genus", {"family": family})
    return JsonResponse(genus_list, safe=False)

@require_GET
def get_species_by_genus(request):
    """Retrieves all species belonging to a specified genus"""
    genus = request.GET.get("genus")
    if not genus:
        return JsonResponse({"error": "Genus not provided"}, status=400)

    species_list = db["species"].distinct("species", {"genus": genus})
    return JsonResponse(species_list, safe=False)

@require_GET
def get_family_by_genus(request):
    """Retrieves family name for a specified genus"""
    genus = request.GET.get("genus")
    if not genus:
        return JsonResponse({"error": "Genus not provided"}, status=400)

    families = db["species"].distinct("family", {"genus": genus})
    return JsonResponse(families, safe=False)

@require_GET
def get_family_by_species(request):
    """Retrieves family name for a specified species"""
    species = request.GET.get("species")
    if not species:
        return JsonResponse({"error": "Species not provided"}, status=400)

    families = db["species"].distinct("family", {"species": species})
    return JsonResponse(families, safe=False)

@require_GET
def get_genus_by_species(request):
    """Retrieves genus name for a specified species"""
    species = request.GET.get("species")
    if not species:
        return JsonResponse({"error": "Species not provided"}, status=400)

    genera = db["species"].distinct("genus", {"species": species})
    return JsonResponse(genera, safe=False)

@require_GET
def get_all_taxa(request):
    """
    Retrieves complete taxonomy hierarchy.
    Returns distinct families, genera, and species from database.
    """
    try:
        # Fetches distinct values for each taxonomic level
        families_raw = db["species"].distinct("family")
        genera_raw = db["species"].distinct("genus")
        species_raw = db["species"].distinct("species")

        # Filters out None values and then sorts alphabetically
        families = sorted([f for f in families_raw if f is not None])
        genera = sorted([g for g in genera_raw if g is not None])
        species_names = sorted([s for s in species_raw if s is not None]) 

        return JsonResponse({
            "families": families,
            "genera": genera,
            "species": species_names,
        })
    except Exception as e:
        print(f"Error in get_all_taxa: {e}")
        return JsonResponse(
            {"error": "An internal server error occurred while fetching taxa.", "details": str(e)},
            status=500
        )

@require_GET
def filter_taxa_options(request):
    """
    Filters taxonomy options based on selected family/genus/species.
    Returns available options at each taxonomic level.
    """
    # Builds query based on provided filters
    query = {}
    if (family := request.GET.get("family")) and family != "All":
        query["family"] = family
    if (genus := request.GET.get("genus")) and genus != "All":
        query["genus"] = genus
    if (species := request.GET.get("species")) and species != "All":
        query["species"] = species

    # Aggregation pipeline to get available options
    pipeline = [
        {"$match": query},
        {
            "$group": {
                "_id": None,
                "families": {"$addToSet": "$family"},
                "genera": {"$addToSet": "$genus"},
                "species": {"$addToSet": "$species"},
            }
        },
        {
            "$project": {
                "_id": 0,
                "families": 1,
                "genera": 1,
                "species": 1
            }
        }
    ]

    # Executes pipeline and return results
    result = list(db["species"].aggregate(pipeline))
    return JsonResponse(result[0] if result else {
        "families": [],
        "genera": [],
        "species": []
    })

def get_continent_js_function():
    """
    Generates JavaScript function for MongoDB to determine continent.
    Used for server-side geospatial queries.
    """
    js_conditions = []
    for continent, polygon in CONTINENT_POLYGONS.items():
        coords = ",".join([f"[{x},{y}]" for x,y in polygon.exterior.coords])
        js_conditions.append(f"""
            if (isPointInPolygon(point.coordinates, [{coords}])) {{
                return "{continent}";
            }}
        """)
    
    return f"""
        function isPointInPolygon(point, polygon) {{
            // Ray casting algorithm implementation
            let inside = false;
            for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {{
                const xi = polygon[i][0], yi = polygon[i][1];
                const xj = polygon[j][0], yj = polygon[j][1];
                
                const intersect = ((yi > point[1]) != (yj > point[1]))
                    && (point[0] < (xj - xi) * (point[1] - yi) / (yj - yi) + xi);
                if (intersect) inside = !inside;
            }}
            return inside;
        }}
        
        const point = {{type: "Point", coordinates: [longitude, latitude]}};
        {''.join(js_conditions)}
        return "Unknown";
    """

@require_GET
def filter_observations(request):
    """
    Filters observations based on taxonomy, date range, and continent.
    Returns GeoJSON FeatureCollection of matching observations.
    """

    # Validates Authorization header and decode JWT token
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Authorization token required"}, status=401)

    token = auth_header[len("Bearer "):]

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id_from_token = payload.get("user_id")
        if not user_id_from_token:
            return JsonResponse({"error": "Invalid token: no user_id"}, status=401)
    except jwt.ExpiredSignatureError:
        return JsonResponse({"error": "Token expired"}, status=401)
    except jwt.InvalidTokenError:
        return JsonResponse({"error": "Invalid token"}, status=401)

    # Parses and validates filter parameters
    try:
        family = request.GET.get("family")
        genus = request.GET.get("genus")
        species = request.GET.get("species")
        continent_filter = request.GET.get("continent", "All Continents")

        start_date = datetime.fromisoformat(request.GET["start_date"])
        end_date = datetime.fromisoformat(request.GET["end_date"])
    except (KeyError, ValueError) as e:
        logger.error(f"Invalid date format or missing date param: {e}")
        return JsonResponse(
            {"error": "Valid start_date and end_date (ISO format) are required"},
            status=400
        )

    if not (family or genus or species):
        return JsonResponse(
            {"error": "At least one of family, genus or species must be provided"},
            status=400
        )

    # Builds species query for filtering species collection
    species_query = {}
    if family and family != "All":
        species_query["family"] = family
    if genus and genus != "All":
        species_query["genus"] = genus
    if species and species != "All":
        species_query["species"] = species

    # Queries species collection to get matching species IDs
    matching_species_ids = db["species"].distinct("_id", species_query)

    # Validates user_id from token as ObjectId
    try:
        user_object_id = ObjectId(user_id_from_token)
    except Exception:
        return JsonResponse({"error": "Invalid user_id in token"}, status=400)

    show_only_my_observations = request.GET.get("show_only_my_observations", "false").lower() == "true"
    
    # Builds MongoDB aggregation match stage including user_id filter
    match_stage = {
        "species_id": {"$in": matching_species_ids},
        "timestamp": {"$gte": start_date, "$lte": end_date},
    }

    if show_only_my_observations:
        match_stage["user_id"] = user_object_id

    # Builds aggregation pipeline
    pipeline = [
        {"$match": match_stage},
        {
            "$lookup": {
                "from": "species",
                "localField": "species_id",
                "foreignField": "_id",
                "as": "species"
            }
        },
        {"$unwind": "$species"},
        {
            "$lookup": {
                "from": "locations",
                "localField": "location_id",
                "foreignField": "_id",
                "as": "location"
            }
        },
        {"$unwind": "$location"},
        {
            "$addFields": {
                "family": "$species.family",
                "genus": "$species.genus",
                "species_name": "$species.species",
                "location_name": "$location.name",
                "location_coords": "$location.geojson.coordinates",
                "country": "$location.country"
            }
        },
        {
            "$project": {
                "species": 0,
                "location": 0
            }
        }
    ]

    try:
        observations = list(db["observations"].aggregate(pipeline))
    except Exception as e:
        logger.error(f"Error running aggregation: {e}")
        return JsonResponse({"error": "Error fetching observations"}, status=500)

    # Processes observations, filters by continent if needed, builds GeoJSON features
    features = []
    for obs in observations:
        coords = obs.get("location_coords", [])
        if not coords or len(coords) != 2:
            continue
        lon, lat = coords  

        continent = get_continent(lat, lon)
        if continent_filter != "All Continents" and continent != continent_filter:
            continue

        feature = {
            "type": "Feature",
            "location": {
                "type": "Point",
                "coordinates": [lon, lat],
                "longitude": lon,
                "latitude": lat
            },
            "properties": {
                "species": obs.get("species_name", ""),
                "genus": obs.get("genus", ""),
                "family": obs.get("family", ""),
                "timestamp": obs.get("timestamp", "").isoformat() if obs.get("timestamp") else "",
                "location_name": obs.get("location_name", ""),
                "country": obs.get("country", ""),
                "photo": obs.get("photo", []),
                "external_link": obs.get("external_link", "")
            }
        }
        features.append(feature)

    return JsonResponse({
        "type": "FeatureCollection",
        "features": features
    }, safe=False)


def convert_bson(value):
    """
    Converts BSON objects to JSON-serializable formats.
    Handles ObjectId, datetime, and nested structures.
    """
    if isinstance(value, dict):
        return {k: convert_bson(v) for k, v in value.items()}
    elif isinstance(value, (list, tuple)):
        return [convert_bson(v) for v in value]
    elif isinstance(value, datetime):  
        return value.isoformat()
    elif isinstance(value, ObjectId):
        return str(value)
    return value


@csrf_exempt
@require_http_methods(["GET", "POST"])
def observation_detail(request, source_id):
    """
    Handles observation detail view (GET) and comment submission (POST).
    Returns complete observation data including taxonomy, location, and comments.
    """
    try:
        auth_header = request.headers.get('Authorization')
        current_user_oid = None
        is_admin = False
        is_current_user = False
        current_user = None

        # Checks authentication if header exists
        if auth_header and len(auth_header.split(' ')) == 2:
            token = auth_header.split(' ')[1]
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                user_id = payload.get("user_id")
                if user_id:
                    current_user_oid = ObjectId(user_id)
                    current_user = users_collection.find_one({"_id": current_user_oid})
                    if current_user:
                        is_admin = "admin" in current_user.get("roles", [])
            except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
                logger.warning(f"Invalid or expired token in observation_detail: {e}")

        # Gets observation by source_id
        observation = observations_collection.find_one({"source_id": int(source_id)})
        if not observation:
            return JsonResponse({"error": "Observation not found"}, status=404)

        observation_id = observation["_id"]
        observation_user_id = observation.get("user_id")
        if current_user_oid and observation_user_id:
            is_current_user = (current_user_oid == observation_user_id)

        # --- Handles POST: Add comment ---
        if request.method == "POST":
            if not current_user_oid:
                return JsonResponse({"error": "Authentication required to post comments"}, status=401)
            
            try:
                body = json.loads(request.body)
                comment_text = body.get("comment_text", "").strip()
                parent_comment_id = body.get("parent_comment_id")

                if not comment_text:
                    return JsonResponse({"error": "Comment cannot be empty"}, status=400)

                comment_doc = {
                    "user_id": current_user_oid,
                    "observation_id": observation_id,
                    "comment_text": comment_text,
                    "timestamp": datetime.utcnow()
                }

                # Handles reply comments
                if parent_comment_id:
                    try:
                        parent_oid = ObjectId(parent_comment_id)
                        if comments_collection.find_one({"_id": parent_oid}):
                            comment_doc["parent_comment_id"] = parent_oid
                        else:
                            return JsonResponse({"error": "Parent comment not found"}, status=400)
                    except Exception:
                        return JsonResponse({"error": "Invalid parent_comment_id"}, status=400)

                # Inserts comment and updates count
                inserted = comments_collection.insert_one(comment_doc)
                observations_collection.update_one({"_id": observation_id}, {"$inc": {"comments_count": 1}})

                return JsonResponse({
                    "success": True,
                    "message": "Comment added successfully.",
                    "comment": convert_bson(comment_doc)
                }, status=201)

            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON"}, status=400)

        # --- Handles GET: Observation detail view ---

        # Gets taxonomy information from either species_id or raw_taxonomy
        species_data = {}
        if "species_id" in observation:
            species = species_collection.find_one({"_id": observation["species_id"]}) or {}
            species_data = {
                "species": species.get("species", ""),
                "common_name": species.get("common_name", ""),
                "family": species.get("family", ""),
                "genus": species.get("genus", ""),
                "taxonomy_source": "species_collection"
            }
        elif "raw_taxonomy" in observation:
            raw_tax = observation["raw_taxonomy"]
            species_data = {
                "species": raw_tax.get("species", "All"),
                "common_name": "",
                "family": raw_tax.get("family", ""),
                "genus": raw_tax.get("genus", "All"),
                "taxonomy_source": "raw_taxonomy"
            }
        else:
            species_data = {
                "species": "",
                "common_name": "",
                "family": "",
                "genus": "",
                "taxonomy_source": "none"
            }

        user = users_collection.find_one({"_id": observation.get("user_id")}) or {}
        location = locations_collection.find_one({"_id": observation.get("location_id")}) or {}

        # Handles coordinates from either geojson or direct fields
        coords = location.get("geojson", {}).get("coordinates", [])
        if not coords or len(coords) != 2:
            latitude_direct = location.get("latitude")
            longitude_direct = location.get("longitude")
            if latitude_direct is not None and longitude_direct is not None:
                coords = [longitude_direct, latitude_direct]
            else:
                coords = [None, None]

        longitude, latitude = coords[0], coords[1]

        # Gets all comments for this observation
        comments_cursor = comments_collection.find({"observation_id": observation_id}).sort("timestamp", 1)
        all_comments = []
        for comment in comments_cursor:
            comment = convert_bson(comment)
            comment["_id"] = str(comment["_id"])
            if "parent_comment_id" in comment:
                comment["parent_comment_id"] = str(comment["parent_comment_id"])
            all_comments.append(comment)

        # Builds comment tree structure
        comment_dict = {c["_id"]: c for c in all_comments}
        for comment in all_comments:
            comment["replies"] = []
            comment["user_name"] = "Anonymous"
            comment["user_profile_picture"] = ""

            # Adds commenter info if available
            commenter = users_collection.find_one({"_id": ObjectId(comment["user_id"])}) if comment.get("user_id") else None
            if commenter:
                pic = commenter.get("profile_picture") or ""
                if pic.startswith("http"):
                    profile_picture_url = pic
                elif pic.startswith("/media/"):
                    profile_picture_url = request.build_absolute_uri(pic)
                else:
                    profile_picture_url = urljoin(request.build_absolute_uri(settings.MEDIA_URL), pic.lstrip("/"))

                comment["user_name"] = commenter.get("username", "Anonymous")
                comment["user_profile_picture"] = profile_picture_url

        # Builds hierarchical comment structure
        top_level_comments = []
        for comment in all_comments:
            parent_id = comment.get("parent_comment_id")
            if parent_id and parent_id in comment_dict:
                comment_dict[parent_id]["replies"].append(comment)
            else:
                top_level_comments.append(comment)
            
        # Sorts replies chronologically
        for comment in all_comments:
            if 'replies' in comment:
                comment['replies'].sort(key=lambda x: x['timestamp'])
        
        # Sorts top-level comments
        top_level_comments.sort(key=lambda x: x['timestamp']) # Sort top-level comments

        # Processes user profile picture URL
        user_pic = user.get("profile_picture") or ""
        if not user_pic:
            user_profile_picture_url = ""
        elif user_pic.startswith("http"):
            user_profile_picture_url = user_pic
        elif user_pic.startswith("/media/"):
            user_profile_picture_url = request.build_absolute_uri(user_pic)
        else:
            user_profile_picture_url = urljoin(request.build_absolute_uri(settings.MEDIA_URL), user_pic.lstrip("/"))

        # Helper function to build full media URLs
        def get_full_media_url(relative_path, request, settings):
            if not relative_path:
                return ""
            relative_path = str(relative_path)
            if relative_path.startswith(("http://", "https://")):
                return relative_path
            elif relative_path.startswith("/media/"):
                return request.build_absolute_uri(relative_path)
            else:
                return urljoin(request.build_absolute_uri(settings.MEDIA_URL), relative_path.lstrip("/"))

        # Processes observation photos
        photos_from_db = observation.get("photo", [])
        processed_photos = [get_full_media_url(p, request, settings) for p in photos_from_db]

        # Processes observation audio
        audio_from_db = observation.get("audio", [])
        processed_audio = [get_full_media_url(a, request, settings) for a in audio_from_db]

        # Generates user-friendly title based on available taxonomy
        user_title = ""
        if species_data["species"] and species_data["species"] != "All":
            if species_data["common_name"]:
                user_title = f'{species_data["species"]} ({species_data["common_name"]})'
            else:
                user_title = species_data["species"]
        elif species_data["genus"] and species_data["genus"] != "All":
            user_title = f'{species_data["genus"]} (genus)'
        elif species_data["family"]:
            user_title = f'{species_data["family"]} (family)'
        else:
            user_title = "Unidentified species"

        # Builds final response structure
        data = {
            "type": "Feature",
            "source_id": observation["source_id"],
            "location": {
                "type": "Point",
                "coordinates": [longitude, latitude] if longitude is not None and latitude is not None else [None, None],
                "latitude": latitude,
                "longitude": longitude
            },
            "properties": {
                "species": species_data["species"],
                "common_name": species_data["common_name"],
                "family": species_data["family"],
                "genus": species_data["genus"],
                "taxonomy_status": "complete" if "species_id" in observation else "partial",
                "timestamp": observation.get("timestamp", ""),
                "location_name": location.get("name", ""),
                "region": location.get("region", ""),
                "country": location.get("country", ""),
                "photo": processed_photos,
                "audio": processed_audio,
                "quantity": observation.get("quantity", 0),
                "additional_details": observation.get("additional_details", ""),
                "external_link": observation.get("external_link", "")
            },
            "species_name": species_data["species"], 
            "user_name": user.get("username", "Anonymous") if observation.get("user_id") else "Anonymous",
            "user_id": str(observation.get("user_id")) if observation.get("user_id") else None,
            "user_profile_picture": user_profile_picture_url,
            "user_title": user_title,
            "status": observation.get("status", ""),
            "comments_count": len(all_comments),
            "comments": top_level_comments,
            "is_admin": is_admin,
            "is_current_user": is_current_user,
            "needs_taxonomy": observation.get("status") == "pending"
        }

        return JsonResponse(convert_bson(data), safe=False)

    except Exception as e:
        logger.error(f"Error in observation_detail: {str(e)}", exc_info=True)
        return JsonResponse({"error": "An error occurred while processing your request", "details": str(e)}, status=500)

    
@require_GET
def search_species_by_name(request):
    """
    Searches species by name or common name.
    Returns matching species with basic taxonomy info.
    """
    term = request.GET.get("q", "").strip()
    if not term:
        return JsonResponse([], safe=False)

    # Case-insensitive search on species name or common name
    query = {
        "$or": [
            {"common_name": {"$regex": term, "$options": "i"}},
            {"species": {"$regex": term, "$options": "i"}},
        ]
    }

    results = db["species"].find(query, {
        "_id": 0, 
        "family": 1, 
        "genus": 1, 
        "species": 1, 
        "common_name": 1
        })
    return JsonResponse(list(results), safe=False)

@require_GET
def search_species_and_users(request):
    """
    Combined search for species and users.
    Returns unified results with type indicators.
    """
    term = request.GET.get("q", "").strip()
    if not term:
        return JsonResponse([], safe=False)

    # Species search query
    species_query = {
        "$or": [
            {"common_name": {"$regex": term, "$options": "i"}},
            {"species": {"$regex": term, "$options": "i"}},
            {"family": {"$regex": term, "$options": "i"}},
            {"genus": {"$regex": term, "$options": "i"}},
        ]
    }
    species_results = list(db["species"].find(species_query, {
        "_id": 1, "family": 1, "genus": 1, "species": 1, "common_name": 1
    }).limit(10))
    for s in species_results:
        s["type"] = "species"

    # Users search query
    user_query = {
        "$or": [
            {"name": {"$regex": term, "$options": "i"}},
            {"username": {"$regex": term, "$options": "i"}},
        ]
    }
    users_results = list(db["users"].find(user_query, {
        "_id": 1, "name": 1, "username": 1
    }).limit(10))
    for u in users_results:
        u["type"] = "user"

    # Formats results
    def format_species(s):
        return {
            "id": str(s["_id"]),
            "family": s.get("family", ""),
            "genus": s.get("genus", ""),
            "species": s.get("species", ""),
            "common_name": s.get("common_name", ""),
            "type": s["type"],
        }

    def format_user(u):
        return {
            "id": str(u["_id"]),
            "name": u.get("name", ""),
            "username": u.get("username", ""),
            "type": u["type"],
        }

    # Combines and returns results
    results = [format_species(s) for s in species_results] + [format_user(u) for u in users_results]

    return JsonResponse(results, safe=False)

@require_GET
def homepage_stats(request):
    """Returns basic statistics for homepage display"""
    species_count = db["species"].count_documents({})
    user_count = db["users"].count_documents({})
    obs_count = db["observations"].count_documents({})
    return JsonResponse({
        "speciesCount": species_count,
        "contributorCount": user_count,
        "observationCount": obs_count
    })

@require_GET
def recent_uploads(request):
    """Gets most recent observations for display on homepage"""
    try:
        # Base media URL for building absolute paths
        media_root_url = request.build_absolute_uri(settings.MEDIA_URL)  # e.g. http://localhost:8000/media/

        pipeline = [
            {"$sort": {"timestamp": -1}},
            {"$limit": 3},
            {"$lookup": {
                "from": "species",
                "localField": "species_id",
                "foreignField": "_id",
                "as": "species_doc"
            }},
            {"$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user_doc"
            }},
            {"$lookup": {
                "from": "locations",
                "localField": "location_id",
                "foreignField": "_id",
                "as": "location_doc"
            }},
            {"$lookup": {
                "from": "comments",
                "localField": "_id",
                "foreignField": "observation_id",
                "as": "comments"
            }},
            {"$project": {
                "species": {"$arrayElemAt": ["$species_doc.species", 0]},
                "common_name": {"$arrayElemAt": ["$species_doc.common_name", 0]},
                "user": {"$arrayElemAt": ["$user_doc.username", 0]},
                "user_name": {"$arrayElemAt": ["$user_doc.name", 0]},
                "location": {
                    "$let": {
                        "vars": {
                            "locationDoc": { "$arrayElemAt": ["$location_doc", 0] }
                        },
                        "in": {
                            "$cond": [
                                { "$or": [
                                    { "$eq": ["$$locationDoc.name", None] },
                                    { "$eq": ["$$locationDoc.name", ""] }
                                ]},
                                {
                                    "$cond": [
                                        { "$or": [
                                            { "$eq": ["$$locationDoc.region", None] },
                                            { "$eq": ["$$locationDoc.region", ""] }
                                        ]},
                                        "$$locationDoc.country",
                                        "$$locationDoc.region"
                                    ]
                                },
                                "$$locationDoc.name"
                            ]
                        }
                    }
                },
                "description": "$additional_details",
                "timestamp": 1,
                "photo": 1,
                "comments": 1,
                "source_id": 1,
                "species_image_url": {"$arrayElemAt": ["$species_doc.image_url", 0]}
            }}
        ]

        uploads = list(db["observations"].aggregate(pipeline))
        processed_uploads = []

        for u in uploads:
            # Formats timestamp for display
            ts = u.get("timestamp")
            if isinstance(ts, datetime):
                date_str = ts.strftime("%d %b %Y")
            elif isinstance(ts, str):
                try:
                    date_str = datetime.fromisoformat(ts).strftime("%d %b %Y")
                except ValueError:
                    date_str = ts
            else:
                date_str = ""

            # Gets submitter name (prefers full name, fallbacks to username)
            submitter_name = u.get("user_name") or u.get("user") or "Anonymous"

            # Processes photo URLs
            processed_photos = []
            photo_list = u.get("photo", [])
            if not isinstance(photo_list, list):
                photo_list = []

            for photo in photo_list:
                if photo.startswith("http://") or photo.startswith("https://"):
                    processed_photos.append(photo)
                elif photo.startswith("/media/"):
                    processed_photos.append(request.build_absolute_uri(photo))
                else:
                    processed_photos.append(urljoin(media_root_url, photo.lstrip("/")))

            # Gets thumbnail (first photo or species image)
            thumbnail = None
            if processed_photos:
                thumbnail = processed_photos[0]
            elif u.get("species_image_url"):
                thumbnail = u["species_image_url"]

            # Processes comments
            processed_comments = []
            for c in u.get("comments", []):
                ts = c.get("timestamp")
                if isinstance(ts, datetime):
                    comment_ts = ts.isoformat()
                elif isinstance(ts, str):
                    comment_ts = ts
                else:
                    comment_ts = ""

                processed_comments.append({
                    **c,
                    "timestamp": comment_ts
                })

            processed_uploads.append({
                "species": u.get("species", "Unknown species"),
                "common_name": u.get("common_name", ""),
                "user": submitter_name,
                "location": u.get("location", "Unknown location"),
                "description": u.get("description", ""),
                "date": date_str,
                "photos": processed_photos,
                "thumbnail": thumbnail,
                "comments": processed_comments,
                "source_id": u.get("source_id", ""),
                "timestamp": ts.isoformat() if isinstance(ts, datetime) else ts
            })

        return JsonResponse(convert_bson(processed_uploads), safe=False)

    except Exception as e:
        print(" ERROR in recent_uploads view:", e)
        traceback.print_exc()
        return HttpResponseServerError("Internal Server Error: " + str(e))


# Creates database indexes for performance
species_collection.create_index("species", unique=True)
locations_collection.create_index([("geojson", "2dsphere")])

def get_location_details(latitude, longitude):
    """
    Reverses geocode coordinates to get location details using OpenStreetMap.
    Returns name, country, and region if available.
    """

    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}"
    headers = {'User-Agent': 'BiodiversityTracker/1.0 (RuthMary.Kurian@autonoma.cat)'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if not data or "address" not in data:
            logger.warning("[LOCATION] Malformed response from API. Skipping.")
            return {"name": "", "country": "", "region": ""}
        return {
            "name": data.get("address", {}).get("city", ""),
            "country": data.get("address", {}).get("country", ""),
            "region": data.get("address", {}).get("state", "")
        }
    except requests.RequestException as e:
        logger.error(f"[LOCATION] Error fetching location details: {e}")
        return {"name": "", "country": "", "region": ""}

@csrf_exempt
@require_http_methods(["POST", "PATCH"])
def upload_observation(request):
    """
    Handles observation uploads (POST) and updates (PATCH).
    Processes taxonomy, location, media, and other observation data.
    """
    try:
        logger.debug(f"Received {request.method} request to /api/upload/")

        # --- Authenticates user ---
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            logger.warning("Authorization header missing or invalid.")
            return JsonResponse({"error": "Authorization header missing or invalid"}, status=401)

        token = auth_header.split(' ')[1]
        user_id = None
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = payload["user_id"]
            user = users_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                logger.warning(f"User not found for ID: {user_id}")
                return JsonResponse({"error": "User not found"}, status=404)
            logger.debug(f"User authenticated: {user_id}")
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired.")
            return JsonResponse({"error": "Token expired"}, status=401)
        except jwt.InvalidTokenError:
            logger.warning("Invalid token provided.")
            return JsonResponse({"error": "Invalid token"}, status=401)
        except Exception as e:
            logger.error(f"JWT decoding error or user lookup: {e}", exc_info=True)
            return JsonResponse({"error": "Authentication failed"}, status=401)

        # --- Parses multipart data for PATCH requests ---
        if request.method == "PATCH":
            try:
                data, files = MultiPartParser(request.META, request, request.upload_handlers).parse()
            except Exception as e:
                logger.error(f"Failed to parse multipart/form-data for PATCH request: {e}", exc_info=True)
                return JsonResponse({"error": "Invalid multipart/form-data for PATCH request"}, status=400)
        else:
            data = request.POST
            files = request.FILES

        logger.debug(f"Request POST data (form fields): {data.dict()}")
        logger.debug(f"Request FILES data (uploaded files): {[f.name for f in files.values()]}")

        is_editing = request.method == "PATCH"
        current_observation = None
        source_id = None

        if is_editing:
            source_id_str = request.GET.get("source_id")
            logger.debug(f"Edit mode detected. source_id_str from GET: {source_id_str}")
            
            if not source_id_str:
                logger.error("PATCH request to /api/upload/ missing 'source_id' in URL query parameters.")
                return JsonResponse({"error": "Missing source_id for edit (expected in URL query)"}, status=400)
            
            try:
                source_id = int(source_id_str)
            except ValueError:
                logger.error(f"Invalid source_id format: {source_id_str}")
                return JsonResponse({"error": "Invalid source_id format (must be an integer)"}, status=400)

            current_observation = observations_collection.find_one({"source_id": source_id})
            if not current_observation:
                logger.warning(f"Observation not found for source_id: {source_id}")
                return JsonResponse({"error": "Observation not found"}, status=404)
            logger.debug(f"Current observation fetched for PATCH: _id={current_observation['_id']}, source_id={current_observation['source_id']}")
            
            # Authorization check for editing
            is_owner = str(current_observation['user_id']) == user_id
            is_admin = "admin" in user.get('roles', [])
            if not (is_owner or is_admin):
                logger.warning(f"User {user_id} not authorized to edit observation {source_id}. Owner: {current_observation['user_id']}, Admin: {is_admin}")
                return JsonResponse({"error": "Not authorized to edit this observation"}, status=403)

        update_fields = {}
        
        # --- Taxonomy Handling ---
        raw_family = data.get('family')
        raw_genus = data.get('genus', 'All')
        raw_species = data.get('species', 'All')

        if not is_editing:  # For new observations
            if not raw_family:
                logger.warning("Missing required family field for new observation")
                return JsonResponse({"error": "Family is required"}, status=400)

        # Checks if taxonomy is complete (no "All" values)
        is_complete_taxonomy = (raw_genus != "All" and raw_species != "All")

        species_id_to_use = None
        if is_complete_taxonomy:
            # Only interacts with species collection for complete taxonomy
            species_doc = species_collection.find_one({
                "species": raw_species,
                "genus": raw_genus,
                "family": raw_family
            })
            
            if not species_doc:
                logger.info(f"Creating new species: {raw_family}, {raw_genus}, {raw_species}")
                species_doc = {
                    "species": raw_species,
                    "genus": raw_genus,
                    "family": raw_family,
                    "common_name": data.get("common_name", raw_species),
                    "image_url": "",
                    "audio_url": "",
                    "observations_count": 0,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                species_id_to_use = species_collection.insert_one(species_doc).inserted_id
            else:
                species_id_to_use = species_doc["_id"]
            
            # Handles species_id in update_fields
            if is_editing:
                if species_id_to_use != current_observation.get("species_id"):
                    update_fields["species_id"] = species_id_to_use
                    # Removes raw taxonomy if previously stored
                    if "raw_taxonomy" in current_observation:
                        update_fields["$unset"] = {"raw_taxonomy": ""}
                    logger.debug(f"Species ID changed from {current_observation.get('species_id')} to {species_id_to_use}")
                else:
                    logger.debug("Species ID remains the same")
            else:  
                update_fields["species_id"] = species_id_to_use
        else:
            # Stores raw taxonomy with "All" placeholders in observation
            update_fields["raw_taxonomy"] = {
                "family": raw_family,
                "genus": raw_genus,
                "species": raw_species
            }
            # Sets status to indicate taxonomy needs completion
            update_fields["status"] = "pending"
            
            # If editing and previously had species_id, removes it
            if is_editing and current_observation.get("species_id"):
                update_fields["$unset"] = {"species_id": ""}
            
            logger.info("Storing incomplete taxonomy in observation (not in species collection)")

        # --- Location Coordinates and ID ---
        latitude, longitude = None, None
        if 'latitude' in data and 'longitude' in data:
            try:
                latitude = float(data['latitude'])
                longitude = float(data['longitude'])
            except (ValueError, TypeError):
                logger.warning(f"Invalid coordinates: lat={data.get('latitude')} lon={data.get('longitude')}")
                return JsonResponse({"error": "Invalid coordinates (must be real numbers)"}, status=400)
            
            location_name = data.get('location_name', 'Unnamed Location')
            try:
                location_info = get_location_details(latitude, longitude) 
                country = location_info.get('country', 'Unknown')
                region = location_info.get('region', 'Unknown')
                logger.debug(f"Location details fetched: country={country}, region={region}")
            except Exception as e:
                logger.error(f"Location fetch error: {e}", exc_info=True)
                country = region = 'Unknown'

            # Checks for existing nearby location (within 10 meters)
            existing_location = locations_collection.find_one({
                "geojson": {
                    "$near": {
                        "$geometry": {"type": "Point", "coordinates": [longitude, latitude]},
                        "$maxDistance": 10 
                    }
                }
            })

            location_id_to_use = None
            if existing_location:
                location_id_to_use = existing_location["_id"]
                logger.debug(f"Found existing location: {location_id_to_use}")

                # Updates location name if it changed
                if existing_location.get("name") != location_name:
                    locations_collection.update_one(
                        {"_id": location_id_to_use},
                        {"$set": {"name": location_name, "updated_at": datetime.utcnow()}}
                    )
                    logger.info(f"Updated location name for {location_id_to_use} to {location_name}")
            else:
                logger.info(f"Creating new location: {location_name} ({latitude}, {longitude})")
                location_doc = {
                    "latitude": latitude,
                    "longitude": longitude,
                    "name": location_name,
                    "country": country,
                    "region": region,
                    "geojson": {
                        "type": "Point",
                        "coordinates": [longitude, latitude]
                    },
                    "source": "manual",
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                location_id_to_use = locations_collection.insert_one(location_doc).inserted_id
            
            # Only updates location_id in update_fields if it's new or has changed
            if is_editing:
                if location_id_to_use != current_observation.get("location_id"):
                    update_fields["location_id"] = location_id_to_use
                    logger.debug(f"Location ID changed from {current_observation.get('location_id')} to {location_id_to_use}. Adding to update_fields.")
                else:
                    logger.debug(f"Location ID (same as current): {location_id_to_use}. Not adding to update_fields.")
            else: 
                update_fields["location_id"] = location_id_to_use
                logger.debug(f"Setting location_id for new observation: {location_id_to_use}. Adding to update_fields.")

        elif not is_editing: # Required for new observations
            logger.warning("Missing latitude or longitude for new observation.")
            return JsonResponse({"error": "Missing latitude or longitude for new observation"}, status=400)
        elif is_editing and current_observation:
            logger.debug("Coordinates not provided or empty in PATCH. Location ID won't be explicitly updated unless changed.")

        # --- Date/Timestamp ---
        if 'date' in data:
            try:
                observation_date = datetime.fromisoformat(data['date'])
                observation_date_str = observation_date.isoformat() + 'Z'
                # Only updates if the value has genuinely changed
                if is_editing and observation_date_str != current_observation.get("timestamp"):
                    update_fields["timestamp"] = observation_date_str
                    logger.debug(f"Timestamp changed from '{current_observation.get('timestamp')}' to '{observation_date_str}'. Adding to update_fields.")
                elif not is_editing: 
                    update_fields["timestamp"] = observation_date_str
                    logger.debug(f"Setting timestamp for new observation: {observation_date_str}. Adding to update_fields.")
                else: 
                    logger.debug(f"Timestamp provided is identical to current: {observation_date_str}. Not adding to update_fields.")
            except ValueError:
                logger.warning(f"Invalid date format: {data.get('date')}")
                return JsonResponse({"error": "Invalid date format. Use ISO format (YYYY-MM-DD)"}, status=400)
        elif not is_editing: # Required for new observations
            logger.warning("Missing required field: date for new observation.")
            return JsonResponse({"error": "Missing required field: date for new observation"}, status=400)
        elif is_editing and current_observation:
            logger.debug("Date not provided in PATCH. Timestamp won't be explicitly updated unless changed.")

        # --- Quantity ---
        if 'quantity' in data:
            try:
                quantity = int(data['quantity'])
                if quantity < 1:
                    logger.warning(f"Invalid quantity: {quantity}")
                    return JsonResponse({"error": "Quantity must be positive"}, status=400)
                # Only updates if the value has genuinely changed
                if is_editing and quantity != current_observation.get("quantity"):
                    update_fields["quantity"] = quantity
                    logger.debug(f"Quantity changed from {current_observation.get('quantity')} to {quantity}. Adding to update_fields.")
                elif not is_editing: 
                    update_fields["quantity"] = quantity
                    logger.debug(f"Setting quantity for new observation: {quantity}. Adding to update_fields.")
                else: 
                    logger.debug(f"Quantity provided is identical to current: {quantity}. Not adding to update_fields.")
            except ValueError:
                logger.warning(f"Invalid quantity format: {data.get('quantity')}")
                return JsonResponse({"error": "Invalid quantity (must be a number)"}, status=400)
        elif not is_editing: # For new observations, sets a default if not provided
            try:
                quantity = int(data.get('quantity', 1))
                if quantity < 1: 
                    logger.warning(f"Invalid quantity for default: {quantity}")
                    return JsonResponse({"error": "Quantity must be positive"}, status=400)
                update_fields["quantity"] = quantity
                logger.debug(f"Setting default quantity to: {quantity}. Adding to update_fields.")
            except ValueError: 
                logger.warning(f"Invalid quantity format for default: {data.get('quantity')}")
                return JsonResponse({"error": "Invalid quantity (must be a number)"}, status=400)
        elif is_editing and current_observation:
            logger.debug("Quantity not provided in PATCH. Quantity won't be explicitly updated unless changed.")

        # --- Additional Details ---
        if "additional_details" in data:
            received_additional_details = data.get("additional_details", "").strip()
            
            if is_editing:
                if received_additional_details != current_observation.get("additional_details", ""):
                    update_fields["additional_details"] = received_additional_details
                    logger.debug(f"Additional details changed from '{current_observation.get('additional_details')}' to '{received_additional_details}'. Adding to update_fields.")
                else:
                    logger.debug(f"Additional details provided is identical to current. Not adding to update_fields.")
            else: 
                update_fields["additional_details"] = received_additional_details
                logger.debug(f"Setting additional_details for new observation: '{received_additional_details}'. Adding to update_fields.")
        elif not is_editing:
            update_fields["additional_details"] = ""

        # --- Media Handling ---
        current_photo_urls = current_observation.get("photo", []) if is_editing else []
        current_audio_urls = current_observation.get("audio", []) if is_editing else []
        
        desired_photo_urls = data.getlist("existing_photos[]")
        desired_audio_urls = data.getlist("existing_audio[]")
        
        if is_editing:
            photos_to_delete = [url for url in current_photo_urls if url not in desired_photo_urls]
            audios_to_delete = [url for url in current_audio_urls if url not in desired_audio_urls]

            for url in photos_to_delete + audios_to_delete:
                try:
                    path_in_storage = url.replace(settings.MEDIA_URL, '', 1)
                    if default_storage.exists(path_in_storage):
                        default_storage.delete(path_in_storage)
                        logger.info(f"Deleted old file from storage: {path_in_storage}")
                except Exception as e:
                    logger.error(f"Error deleting old file {url}: {e}", exc_info=True)
        
        photo_urls = list(desired_photo_urls)
        audio_urls = list(desired_audio_urls)

        for uploaded_file in files.getlist("media_files"):
            try:
                ext = guess_extension(uploaded_file.content_type) or os.path.splitext(uploaded_file.name)[1] or '.bin'
                filename = f"{uuid.uuid4()}{ext}"
                target_path = f"uploads/{filename}"
                
                saved_name = default_storage.save(target_path, ContentFile(uploaded_file.read()))
                file_url = default_storage.url(saved_name)
                
                if uploaded_file.content_type.startswith('image/'):
                    photo_urls.append(file_url)
                    if update_fields.get("species_id"):
                        species_doc = species_collection.find_one({"_id": update_fields["species_id"]})
                        if species_doc and not species_doc.get("image_url"):
                            species_collection.update_one(
                                {"_id": update_fields["species_id"]},
                                {"$set": {"image_url": file_url, "updated_at": datetime.utcnow()}}
                            )
                elif uploaded_file.content_type.startswith('audio/'):
                    audio_urls.append(file_url)
                    if update_fields.get("species_id"):
                        species_doc = species_collection.find_one({"_id": update_fields["species_id"]})
                        if species_doc and not species_doc.get("audio_url"):
                            species_collection.update_one(
                                {"_id": update_fields["species_id"]},
                                {"$set": {"audio_url": file_url, "updated_at": datetime.utcnow()}}
                            )
            except Exception as e:
                logger.error(f"Error saving new file: {e}", exc_info=True)
                return JsonResponse({'error': 'Failed to save file.'}, status=500)
        
        if photo_urls != current_photo_urls:
            update_fields["photo"] = photo_urls
        if audio_urls != current_audio_urls:
            update_fields["audio"] = audio_urls
        
        if is_editing and update_fields:
            update_fields["updated_at"] = datetime.utcnow()

        # --- Final Update/Insert ---
        if is_editing:
            meaningful_update_fields = {k: v for k, v in update_fields.items() if k != "updated_at"}
            if not meaningful_update_fields:
                return JsonResponse({
                    "success": True,
                    "message": "No changes detected to update.",
                    "observation_id": str(current_observation["_id"]),
                    "source_id": current_observation["source_id"]
                })
            
            result = observations_collection.update_one(
                {"_id": current_observation["_id"]},
                {"$set": update_fields}
            )

            if result.matched_count == 0:
                return JsonResponse({"error": "Failed to update observation: not found"}, status=404)
            
            return JsonResponse({
                "success": True,
                "message": "Observation updated successfully.",
                "observation_id": str(current_observation["_id"]),
                "source_id": current_observation["source_id"]
            })

        # --- New Observation Creation ---
        new_source_id = int(str(uuid.uuid4().int)[:9])
        while observations_collection.find_one({"source_id": new_source_id}):
            new_source_id = int(str(uuid.uuid4().int)[:9])

        observation_doc = {
            "location_id": update_fields["location_id"],
            "timestamp": update_fields["timestamp"],
            "photo": update_fields.get("photo", []),
            "audio": update_fields.get("audio", []),
            "additional_details": update_fields.get("additional_details", ""),
            "quantity": update_fields["quantity"],
            "status": "pending" if "raw_taxonomy" in update_fields else "pending",
            "updated_at": datetime.utcnow(),
            "user_id": ObjectId(user_id),
            "created_at": datetime.utcnow(),
            "source_id": new_source_id,
            "comments_count": 0
        }

        if "species_id" in update_fields:
            observation_doc["species_id"] = update_fields["species_id"]
        if "raw_taxonomy" in update_fields:
            observation_doc["raw_taxonomy"] = update_fields["raw_taxonomy"]

        inserted = observations_collection.insert_one(observation_doc)
        
        if "species_id" in observation_doc:
            species_collection.update_one(
                {"_id": observation_doc["species_id"]},
                {"$inc": {"observations_count": 1}}
            )

        return JsonResponse({
            "success": True,
            "message": "Observation submitted successfully.",
            "observation_id": str(inserted.inserted_id),
            "source_id": new_source_id
        })

    except Exception as e:
        logger.exception("Error in upload_observation:")
        return JsonResponse({"error": "An internal server error occurred", "details": str(e)}, status=500)

@require_GET
@csrf_exempt
def user_profile(request, user_id=None):
    """
    Gets user profile data including statistics and recent observations.
    Requires authentication and checks authorization.
    """
    try:
        # Checks for JWT and get current user ID
        auth_header = request.headers.get('Authorization')
        if not auth_header or len(auth_header.split(' ')) != 2:
            return JsonResponse({"error": "Authorization header missing or malformed"}, status=401)

        token = auth_header.split(' ')[1]
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        current_user_id = payload.get("user_id")
        if not current_user_id:
            return JsonResponse({"error": "Invalid token payload"}, status=401)

        current_user_oid = ObjectId(current_user_id)

        # If user_id not provided in URL, uses current user's ID
        target_user_oid = ObjectId(user_id) if user_id else current_user_oid

        # Fetches current user (for admin check)
        current_user = db.users.find_one({"_id": current_user_oid})
        if not current_user:
            return JsonResponse({"error": "Current user not found"}, status=404)

        is_admin = "admin" in current_user.get("roles", [])
        is_current_user = current_user_oid == target_user_oid

        # Fetches target user data
        user = db.users.find_one({"_id": target_user_oid})
        if not user:
            return JsonResponse({"error": "User not found"}, status=404)

        # Builds absolute media URL root
        media_root_url = request.build_absolute_uri(settings.MEDIA_URL)

        # Applies profile picture URL logic
        pic = user.get("profile_picture", "")
        if pic:
            if pic.startswith("http://") or pic.startswith("https://"):
                profile_picture_url = pic
            elif pic.startswith("/media/"):
                profile_picture_url = request.build_absolute_uri(pic)
            else:
                profile_picture_url = urljoin(media_root_url, pic.lstrip("/"))
        else:
            profile_picture_url = None
        
        # Fetches user's observations with species and location data
        observations = list(db.observations.aggregate([
            {"$match": {"user_id": target_user_oid}},
            {"$sort": {"timestamp": -1}},
            {"$lookup": {
                "from": "species",
                "localField": "species_id",
                "foreignField": "_id",
                "as": "species"
            }},
            {"$lookup": {
                "from": "locations",
                "localField": "location_id",
                "foreignField": "_id",
                "as": "location"
            }},
            {"$project": {
                "_id": 1,
                "source_id": 1,
                "timestamp": 1,
                "status": 1,
                "species": {"$arrayElemAt": ["$species.species", 0]},
                "common_name": {"$arrayElemAt": ["$species.common_name", 0]},
                "location_name": {"$arrayElemAt": ["$location.name", 0]},
                "region": {"$arrayElemAt": ["$location.region", 0]},
                "country": {"$arrayElemAt": ["$location.country", 0]},
                "photo": {"$arrayElemAt": ["$photo", 0]}
            }}
        ]))

        # Fetches latest comment and related observation for activity section
        latest_comment = db.comments.find_one(
            {"user_id": target_user_oid},
            sort=[("timestamp", -1)]
        )

        recent_activity = None
        if latest_comment:
            obs = db.observations.find_one({"_id": latest_comment["observation_id"]})
            if obs:
                species = db.species.find_one({"_id": obs["species_id"]})
                if species:
                    species_name = species.get("common_name") or species.get("species")
                    recent_activity = {
                        "text": f"Commented on {species_name} observation",
                        "timestamp": latest_comment.get("timestamp")
                    }

        # Counts statistics
        stats = {
            "total_observations": db.observations.count_documents({"user_id": target_user_oid}),
            "verified_entries": db.observations.count_documents({
                "user_id": target_user_oid,
                "status": "verified"
            }),
            "comments_count": db.comments.count_documents({"user_id": target_user_oid})
        }

        # Cleans BSON types for JSON response
        user_clean = convert_bson(user)
        observations_clean = convert_bson(observations)

        return JsonResponse({
            "user": {
                "username": user_clean.get("username"),
                "name": user_clean.get("name", ""),
                "profile_picture": profile_picture_url,
                "created_at": user_clean.get("created_at"),
                "is_current_user": is_current_user,
                "is_admin": is_admin
            },
            "observations": observations_clean,
            "stats": stats,
            "recent_activity": recent_activity
        })

    except InvalidId:
        return JsonResponse({"error": "Invalid user ID format"}, status=400)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return JsonResponse({"error": "Invalid or expired token"}, status=401)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@require_http_methods(["GET", "PUT", "PATCH", "DELETE"])
@csrf_exempt
def edit_profile(request, user_id=None):
    """
    Handles profile editing and deletion.
    Supports GET (view), PUT/PATCH (update), and DELETE operations.
    """
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or len(auth_header.split(' ')) != 2:
            return JsonResponse({"error": "Authorization header missing or malformed"}, status=401)

        token = auth_header.split(' ')[1]
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        current_user_id = payload.get("user_id")
        if not current_user_id:
            return JsonResponse({"error": "Invalid token payload"}, status=401)

        current_user_oid = ObjectId(current_user_id)
        target_user_oid = ObjectId(user_id) if user_id else current_user_oid

        # Checks if current user is admin
        current_user = db.users.find_one({"_id": current_user_oid})
        is_admin = "admin" in current_user.get("roles", [])

        # Authorization check
        if not is_admin and target_user_oid != current_user_oid:
            return JsonResponse({"error": "Unauthorized to edit this profile"}, status=403)

        media_root_url = request.build_absolute_uri(settings.MEDIA_URL)

        def process_profile_picture(pic_value):
            if not pic_value:
                return None
            if pic_value.startswith("http://") or pic_value.startswith("https://"):
                return pic_value
            if pic_value.startswith("/media/"):
                return request.build_absolute_uri(pic_value)
            return urljoin(media_root_url, pic_value.lstrip("/"))

        if request.method == "GET":
            # Gets profile data for viewing
            user = db.users.find_one({"_id": target_user_oid})
            if not user:
                return JsonResponse({"error": "User not found"}, status=404)

            observations_count = db.observations.count_documents({"user_id": target_user_oid})
            species_count = len(db.observations.distinct("species_id", {"user_id": target_user_oid}))
            location_ids = db.observations.distinct("location_id", {"user_id": target_user_oid})
            locations = db.locations.find({"_id": {"$in": location_ids}})
            logical_labels = set()
            for loc in locations:
                for key in ["name", "region", "country"]:
                    val = loc.get(key, "").strip()
                    if val:
                        logical_labels.add(val)
                        break

            profile_picture = process_profile_picture(user.get("profile_picture", ""))
            
            return JsonResponse({
                "name": user.get("name", ""),
                "description": user.get("description", ""),
                "profile_picture": profile_picture,
                "observations_count": observations_count,
                "species_count": species_count,
                "locations_count": len(logical_labels),
                "is_current_user": str(target_user_oid) == str(current_user_oid),
                "is_admin": is_admin
            })

        elif request.method in ["PUT", "PATCH"]:
            # Updates profile data
            if not is_admin and target_user_oid != current_user_oid:
                return JsonResponse({"error": "Cannot edit other users' profiles"}, status=403)

            current_user = db.users.find_one({"_id": current_user_oid})
            if not current_user:
                return JsonResponse({"error": "User not found"}, status=404)

            update_fields = {}

            if request.content_type and "multipart/form-data" in request.content_type:
                post_data, files_data = MultiPartParser(request.META, request, request.upload_handlers).parse()

                if 'name' in post_data:
                    update_fields['name'] = post_data.get('name', '').strip()

                if 'description' in post_data:
                    update_fields['description'] = post_data.get('description', '').strip()

                if 'profile_picture' in files_data:
                    file = files_data['profile_picture']
                    ext = os.path.splitext(file.name)[1]
                    filename = f"{uuid.uuid4().hex}{ext}"
                    save_path = os.path.join("profile_pictures", filename)
                    saved_path = default_storage.save(save_path, ContentFile(file.read()))
                    update_fields['profile_picture'] = settings.MEDIA_URL + saved_path
                elif post_data.get('profile_picture') == 'true':
                    update_fields['profile_picture'] = ""

            else:
                try:
                    data = json.loads(request.body.decode('utf-8'))
                    if 'name' in data:
                        update_fields['name'] = data['name'].strip() if data.get('name') is not None else ""
                    if 'description' in data:
                        update_fields['description'] = data['description'].strip() if data.get('description') is not None else ""
                    if 'profile_picture' in data:
                        update_fields['profile_picture'] = "" if data['profile_picture'] is None else data['profile_picture'].strip()
                except (json.JSONDecodeError, UnicodeDecodeError):
                    return JsonResponse({"error": "Invalid JSON body"}, status=400)

            if update_fields:
                db.users.update_one(
                    {"_id": current_user_oid},
                    {"$set": update_fields}
                )

                updated_user = db.users.find_one({"_id": current_user_oid})
                profile_picture = process_profile_picture(updated_user.get("profile_picture", ""))

                return JsonResponse({
                    "message": "Profile updated successfully",
                    "user": {
                        "name": updated_user.get("name", ""),
                        "description": updated_user.get("description", ""),
                        "profile_picture": profile_picture
                    }
                })
            else:
                profile_picture = process_profile_picture(current_user.get("profile_picture", ""))

                return JsonResponse({
                    "message": "No fields provided for update",
                    "user": {
                        "name": current_user.get("name", ""),
                        "description": current_user.get("description", ""),
                        "profile_picture": profile_picture
                    }
                }, status=400)

        elif request.method == "DELETE":
            # Deletes user account and anonymizes their data
            requesting_user = users_collection.find_one({"_id": current_user_oid})
            is_admin = "admin" in requesting_user.get("roles", [])

            if not is_admin and target_user_oid != current_user_oid:
                return JsonResponse({"error": "Cannot delete other users' profiles"}, status=403)

            # Deletes user
            result = db.users.delete_one({"_id": target_user_oid})
            if result.deleted_count == 0:
                return JsonResponse({"error": "User not found"}, status=404)

            # Anonymizes observations
            db.observations.update_many(
                {"user_id": target_user_oid},
                {"$set": {"user_id": None}}
            )

            # Anonymizes their comments by replacing user_id
            db.comments.update_many(
                {"user_id": target_user_oid},
                {"$set": {"user_id": None}} 
            )

            return JsonResponse({"message": "Account deleted and observations anonymized"}, status=204)

    except InvalidId:
        return JsonResponse({"error": "Invalid User ID format."}, status=400)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return JsonResponse({"error": "Invalid or expired token"}, status=401)
    except Exception as e:
        logger.error(f"Error in edit_profile: {str(e)}", exc_info=True)
        return JsonResponse({"error": f"Server error: {str(e)}"}, status=500)

            
def fetch_and_store_all(request=None):
    logger.info("[DEBUG] Starting fetch_and_store_all...")
    
    inserted_species_count = 0
    inserted_observations = 0
    inserted_comments = 0
    max_pages = 50  
    per_page = 200 
    iconic_insecta_id = 47158  # Taxa ID for insects
    total_species_expected = 0
    species_insertion_successful = True

    try:
        # Counts total expected species
        try:
            first_page = get_taxa(
                is_active=True,
                taxon_id=iconic_insecta_id,
                rank="species",
                per_page=1,
                order="desc",
                order_by="observations_count"
            )
            total_species_expected = first_page.get("total_results", 0)
            logger.info(f"[TAXA] Total expected species: {total_species_expected}")
        except Exception as e:
            logger.error(f"[TAXA] Failed to fetch total species count: {e}")
            return JsonResponse({"error": "Failed to fetch species count"}, status=500)

        # Inserts species
        for page in range(1, max_pages + 1):
            logger.info(f"[TAXA] Fetching taxa data (Page: {page})...")
            try:
                taxa_response = get_taxa(
                    is_active=True,
                    taxon_id=iconic_insecta_id,
                    rank="species",
                    per_page=per_page,
                    order="desc",
                    order_by="observations_count",
                    page=page
                )
            except Exception as e:
                logger.error(f"[TAXA] Failed to fetch taxa data: {e}")
                species_insertion_successful = False
                break

            species_to_insert = []
            for taxon in taxa_response.get("results", []):
                species_name = taxon.get("name", "")
                if not species_name:
                    continue
                if species_collection.find_one({"species": species_name}):
                    logger.info(f"[TAXA] Skipping existing species: {species_name}")
                    continue
                if iconic_insecta_id not in taxon.get("ancestor_ids", []):
                    logger.info(f"[TAXA] Skipping non-insect: {species_name}")
                    continue

                ancestors = taxon.get("ancestor_ids", [])
                genus = family = None
                for ancestor_id in reversed(ancestors):
                    try:
                        details = get_taxa(taxon_id=ancestor_id)
                        result = details.get("results", [{}])[0]
                        if not genus and result.get("rank") == "genus":
                            genus = result["name"]
                        if not family and result.get("rank") == "family":
                            family = result["name"]
                        if genus and family:
                            break
                    except Exception as e:
                        logger.error(f"[TAXA] Failed to fetch ancestor details: {e}")
                        continue

                if not genus or not family:
                    logger.warning(f"[TAXA] Skipping {species_name} due to missing family/genus")
                    continue

                species_to_insert.append({
                    "species": species_name,
                    "family": family,
                    "genus": genus,
                    "common_name": taxon.get("preferred_common_name", ""),
                    "image_url": taxon.get("default_photo", {}).get("medium_url", ""),
                    "audio_url": "",
                    "observations_count": 0
                })

            if species_to_insert:
                try:
                    species_collection.insert_many(species_to_insert, ordered=False)
                    inserted_species_count += len(species_to_insert)
                    logger.info(f"[TAXA] Inserted {len(species_to_insert)} species for page {page}.")
                except errors.BulkWriteError as bwe:
                    logger.warning(f"[TAXA] Bulk insert error: {bwe.details}")
                except Exception as e:
                    logger.error(f"[TAXA] Error during bulk insert: {e}")
                    species_insertion_successful = False
                    break

            time.sleep(1)

        # Inserts observations
        for page in range(1, max_pages + 1):
            logger.info(f"[OBS] Fetching observations (Page: {page})...")
            try:
                obs_response = get_observations(iconic_taxa="Insecta", quality_grade="research", page=page, per_page=per_page)
            except Exception as e:
                logger.error(f"[OBS] Failed to fetch observations: {e}")
                continue

            for obs in obs_response.get("results", []):
                taxon = obs.get("taxon", {})
                species_name = taxon.get("name", "")
                if not species_name:
                    logger.info("[OBS] Skipping observation with no species.")
                    continue

                species_doc = species_collection.find_one({"species": species_name})
                if not species_doc:
                    logger.info(f"[OBS] Species not in taxonomy: {species_name}")
                    continue
                species_id = species_doc["_id"]

                # Inserts user data
                user = obs.get("user", {})
                username = f"inaturalist-{user.get('login_exact', '')}"
                user_record = users_collection.find_one({"username": username})

                if user_record:
                    user_id = user_record["_id"]
                    logger.info(f"[USER] Reusing existing user: {username}")
                else:
                    try:
                        user_id = users_collection.insert_one({
                            "username": username,
                            "name": user.get("name", ""),
                            "email": user.get("email", "no-email@example.com"),
                            "password_hash": "",
                            "profile_picture": user.get("icon_url", ""),
                            "source": "inaturalist",
                            "created_at": datetime.strptime(
                                user.get("created_at"), "%Y-%m-%dT%H:%M:%S%z"
                            ) if user.get("created_at") else datetime.utcnow(),
                            "roles": ["user"]
                        }).inserted_id
                        logger.info(f"[USER] Inserted new user: {username}")
                    except Exception as e:
                        logger.error(f"[USER] Failed to insert: {username}, error: {e}")
                        continue

                # Handles location data
                location_id = None
                geojson = obs.get("geojson")
                if geojson and geojson.get("type") == "Point":
                    longitude, latitude = geojson["coordinates"]
                    existing = locations_collection.find_one({
                        "geojson": {
                            "$near": {
                                "$geometry": geojson,
                                "$maxDistance": 10
                            }
                        }
                    })
                    if existing:
                        location_id = existing["_id"]
                    else:
                        loc_data = get_location_details(latitude, longitude)
                        try:
                            location_id = locations_collection.insert_one({
                                "latitude": latitude,
                                "longitude": longitude,
                                "name": loc_data["name"],
                                "country": loc_data["country"],
                                "region": loc_data["region"],
                                "geojson": geojson,
                                "source": "inaturalist"
                            }).inserted_id
                            logger.info(f"[LOC] Inserted new location: {loc_data}")
                        except Exception as e:
                            logger.error(f"[LOC] Failed location insert: {e}")

                # Skips if the observation already exists by source_id
                if observations_collection.find_one({"source_id": obs.get("id")}):
                    logger.info(f"[OBS] Skipping existing observation with ID {obs.get('id')} for species {species_name}.")
                    continue

                # Parses timestamp and inserts observation
                observed_on = obs.get("observed_on")
                try:
                    timestamp = datetime.strptime(obs.get("observed_on_string", ""), "%Y/%m/%d %I:%M %p")
                except Exception:
                    timestamp = observed_on or datetime.utcnow()

                obs_doc = {
                    "user_id": user_id,
                    "species_id": species_id,
                    "location_id": location_id,
                    "timestamp": timestamp,
                    "photo": [
                        re.sub(r'/square\.(jpg|jpeg)$', r'/medium.\1',url)
                        for p in obs.get("observation_photos", [])
                        if "photo" in p and (url := p["photo"].get("medium_url") or p["photo"].get("url"))
                    ],
                    "audio": [s["file_url"] for s in obs.get("sounds", []) if "file_url" in s],
                    "additional_details": obs.get("description", ""),
                    "status": "verified" if obs.get("quality_grade") == "research" else "pending",
                    "source_id": obs.get("id"),
                    "external_link": obs.get("uri"),
                    "comments_count": 1
                }

                try:
                    obs_id = observations_collection.insert_one(obs_doc).inserted_id
                    inserted_observations += 1
                    logger.info(f"[OBS] Inserted observation {obs.get('id')} for species {species_name}.")
                except Exception as e:
                    logger.error(f"[OBS] Insert failed: {e}")
                    continue

                # Inserts comments associated with the observation
                for c in obs.get("comments", []):
                    try:
                        comments_collection.insert_one({
                            "observation_id": obs_id,
                            "user_id": user_id,
                            "comment_text": c.get("body", ""),
                            "timestamp": datetime.strptime(c.get("created_at"), "%Y-%m-%dT%H:%M:%S%z")
                        })
                        inserted_comments += 1
                        logger.info(f"[COMMENT] Inserted comment on observation {obs.get('id')}")
                    except Exception as e:
                        logger.error(f"[COMMENT] Comment insert failed for observation {obs.get('id')}: {e}")

            time.sleep(1)

        # Finalizing: Updates counts for species and comments
        logger.info("[COUNT] Updating species observation counts...")
        for sp in species_collection.find({}, {"_id": 1}):
            count = observations_collection.count_documents({"species_id": sp["_id"]})
            species_collection.update_one({"_id": sp["_id"]}, {"$set": {"observations_count": count}})
            logger.debug(f"[COUNT] Updated species {"_id"} with {count} observations.")

        logger.info("[COUNT] Updating observation comment counts...")
        for obs in observations_collection.find({}, {"_id": 1}):
            count = comments_collection.count_documents({"observation_id": obs["_id"]})
            observations_collection.update_one({"_id": obs["_id"]}, {"$set": {"comments_count": count}})
            logger.debug(f"[COUNT] Updated observation {"_id"} with {count} comments.")

        logger.info(f"[DONE] Fetch and store completed. Species: {inserted_species_count}, Observations: {inserted_observations}, Comments: {inserted_comments}")
        return JsonResponse({
            "species_inserted": inserted_species_count,
            "observations_inserted": inserted_observations,
            "comments_inserted": inserted_comments
        })

    except Exception as e:
        logger.error(f"[FATAL ERROR] Unexpected error in fetch_and_store_all: {e}", exc_info=True)
        return JsonResponse({"error": "An internal error occurred while processing data."}, status=500)

import re
from django.contrib.admin.views.decorators import staff_member_required
from functools import wraps
import csv

@staff_member_required
def upgrade_observation_photos(request):
    """
    Admin utility to upgrade observation photo URLs from square to medium size.
    Runs as a one-time migration.
    """
    updated_count = 0
    total_checked = 0

    for obs in db["observations"].find({"photo": {"$exists": True, "$ne": []}}):
        original_photos = obs["photo"]
        new_photos = []
        changed = False

        for url in original_photos:
            if re.search(r'/square\.(jpg|jpeg)$', url):
                new_url = re.sub(r'/square\.(jpg|jpeg)$', r'/medium.\1', url)
                new_photos.append(new_url)
                changed = True
            else:
                new_photos.append(url)

        if changed:
            db["observations"].update_one(
                {"_id": obs["_id"]},
                {"$set": {"photo": new_photos}}
            )
            updated_count += 1

        total_checked += 1

    return JsonResponse({
        "message": f"{updated_count} observations updated out of {total_checked} checked."
    })

@admin_required
def dashboard_stats(request):
    """
    Gets statistics for admin dashboard.
    Includes counts of contributions, users, and data quality metrics.
    """

    # Gets counts from your database
    total_contributions = db["observations"].count_documents({})
    active_users = db["users"].count_documents({})  
    pending_reviews = db["observations"].count_documents({"status": "pending"})
    
    # Data quality calculation - checks for required fields
    complete_obs = db["observations"].count_documents({
        "species_id": {"$exists": True},
        "location_id": {"$exists": True},
        "timestamp": {"$exists": True},
        "photo": {"$exists": True, "$ne": []}
    })
    data_quality = round((complete_obs / total_contributions) * 100, 1) if total_contributions > 0 else 0
    
    return JsonResponse({
        "stats": [
            {"id": 1, "label": "Total Contributions", "value": total_contributions},
            {"id": 2, "label": "Active Users", "value": active_users},
            {"id": 3, "label": "Pending Reviews", "value": pending_reviews},
            {"id": 4, "label": "Data Completeness", "value": data_quality},
        ]
    })

@csrf_exempt
@require_http_methods(["GET", "POST"])
@admin_required
def recent_users(request):
    """
    Admin view for managing recent users.
    Supports viewing user list and toggling blocked status.
    """
    try:
        # Toggles isBlocked if POST
        if request.method == 'POST':
            body = json.loads(request.body)
            user_id = body.get('user_id')

            if not user_id:
                return JsonResponse({'error': 'User ID not provided'}, status=400)

            user = db["users"].find_one({"_id": ObjectId(user_id)})
            if not user:
                return JsonResponse({'error': 'User not found'}, status=404)

            new_status = not user.get("isBlocked", False)
            db["users"].update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"isBlocked": new_status}}
            )
            return JsonResponse({'message': f'User status updated to {"Blocked" if new_status else "Unblocked"}', 'isBlocked': new_status})
        
        # Defines role priority (higher index = lower priority)
        role_priority = ["admin", "editor", "user"]

        users = list(db["users"].find(
            {},
            {"_id": 1, "username": 1, "name": 1, "roles": 1, "created_at": 1, "profile_picture": 1, "isBlocked": 1}
        ).sort("created_at", -1))

        media_root_url = request.build_absolute_uri(settings.MEDIA_URL)

        for user in users:
            user["id"] = str(user.pop("_id"))

            created_at = user.get("created_at")
            if isinstance(created_at, datetime):
                user["activeDate"] = created_at.strftime("%b %Y")
            else:
                user["activeDate"] = "N/A"

            # Determines the highest role based on role_priority
            roles = user.get("roles", [])
            if roles:
                user["role"] = sorted(roles, key=lambda r: role_priority.index(r) if r in role_priority else len(role_priority))[0]
            else:
                user["role"] = "user"

            user["name"] = user.get("name") or user["username"]


            # Profile picture logic to obtain the complete path
            pic = user.get("profile_picture", "")
            if pic:
                if pic.startswith("http://") or pic.startswith("https://"):
                    user["profile_picture"] = pic
                elif pic.startswith("/media/"):
                    user["profile_picture"] = request.build_absolute_uri(pic)
                else:
                    user["profile_picture"] = urljoin(media_root_url, pic.lstrip("/"))
            else:
                user["profile_picture"] = None

            user["isBlocked"] = user.get("isBlocked", False)

        return JsonResponse({"users": users})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)
    
@csrf_exempt
@require_http_methods(["GET", "POST"])
@admin_required
def pending_content(request):
    """
    Admin view for managing pending content.
    Supports listing pending observations and updating their status.
    """

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            observation_id = data.get('observation_id')
            new_status = data.get('status')

            if not observation_id or not new_status:
                return JsonResponse({'error': 'Observation ID and status are required'}, status=400)

            if new_status not in ['verified', 'rejected']:
                return JsonResponse({'error': 'Invalid status provided'}, status=400)
            
            result = db.observations.update_one(
                {"_id": ObjectId(observation_id)},
                {"$set": {"status": new_status}}
            )

            if result.matched_count == 0:
                return JsonResponse({'error': 'Observation not found'}, status=404)

            return JsonResponse({'message': f'Observation status updated to {new_status}'})
        
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
        
    observations = list(db["observations"].aggregate([
        {"$match": {"status": "pending"}},
        {"$lookup": {
            "from": "species",
            "localField": "species_id",
            "foreignField": "_id",
            "as": "species_info"
        }},
        {"$lookup": {
            "from": "users",
            "localField": "user_id",
            "foreignField": "_id",
            "as": "user_info"
        }},
        {"$lookup": {
            "from": "locations",
            "localField": "location_id",
            "foreignField": "_id",
            "as": "location_info"
        }}
    ]))

    # Base media URL
    media_root_url = request.build_absolute_uri(settings.MEDIA_URL)

    content_items = []
    for obs in observations:
        species = obs["species_info"][0] if obs.get("species_info") else {}
        user = obs["user_info"][0] if obs.get("user_info") else {}
        location = obs["location_info"][0] if obs.get("location_info") else {}

        # Submitter name
        submitter_name = "Anonymous"
        if user:
            submitter_name = user.get("name") or user.get("username") or "Anonymous"
        
        # Location priority: name > region > country
        location_name = location.get("name") or location.get("region") or location.get("country") or "Unknown"

        # Thumbnail complete path logic
        thumbnail = ""
        photo_list = obs.get("photo")
        if not isinstance(photo_list, list):
            photo_list = []

        if photo_list:
            first_photo = photo_list[0]
            if first_photo.startswith("http://") or first_photo.startswith("https://"):
                thumbnail = first_photo
            elif first_photo.startswith("/media/"):
                thumbnail = request.build_absolute_uri(first_photo)
            else:
                thumbnail = urljoin(media_root_url, first_photo.lstrip("/"))
        elif species.get("image_url"):
            thumbnail = species["image_url"]
        else:
            thumbnail = None

        # Parses and formats date robustly
        timestamp_raw = obs.get("timestamp")
        if isinstance(timestamp_raw, datetime):
            formatted_date = timestamp_raw.strftime("%b %d, %Y")
        elif isinstance(timestamp_raw, str):
            try:
                parsed_timestamp = datetime.fromisoformat(timestamp_raw.replace("Z", "+00:00"))
                formatted_date = parsed_timestamp.strftime("%b %d, %Y")
            except ValueError:
                formatted_date = "Unknown"
        else:
            formatted_date = "Unknown"

        # Final content item
        content_items.append({
            "id": str(obs["_id"]),
            "source_id": obs.get("source_id"),
            "species": species.get("common_name") or species.get("species", "Unknown"),
            "submitter": submitter_name,
            "location": location_name,
            "date": formatted_date,
            "thumbnail": thumbnail
        })

    return JsonResponse({"content": content_items})


@user_required
def export_data(request, format_type):
    """
    Handles data export requests in JSON or CSV format.
    Supports user-specific exports and admin full exports.
    """
    try:
        # Gets user info from JWT
        user = request.user_info
        current_user_id = str(user["_id"])
        is_admin = "admin" in user.get("roles", [])

        # Gets target_user_id from query params (if any)
        target_user_id = request.GET.get("target_user_id")
        if target_user_id:
            try:
                target_user_id = str(ObjectId(target_user_id))
            except Exception:
                return JsonResponse({"error": "Invalid target_user_id"}, status=400)
        else:
            target_user_id = None

        collections = db.list_collection_names()

        # Collections only admins can see
        admin_only_collections = ["admin_logs", "celery_tasks", "internal_metrics", "system.indexes"]

        # Collections that are user-owned and should be filtered by user_id
        user_owned_collections = {
            "observations": "user_id",
            "comments": "user_id"
        }

        # Decides which collections to export based on user role and presence of target_user_id
        if is_admin and target_user_id:
            # Admin requesting export of only one user's data for user-owned collections
            collections_to_export = [col for col in collections if col in user_owned_collections]
        elif is_admin and not target_user_id:
            # Admin exporting everything
            collections_to_export = collections
        else:
            # Regular user exporting their own data plus all non-admin collections
            collections_to_export = [col for col in collections if col not in admin_only_collections]

        # Function to get filtered documents depending on context
        def get_filtered_docs(collection_name):
            if is_admin and target_user_id:
                # Admin exporting only target user's data for user-owned collections
                if collection_name in user_owned_collections:
                    field = user_owned_collections[collection_name]
                    return list(db[collection_name].find({field: ObjectId(target_user_id)}))
                else:
                    # No other collections are exported in this mode
                    return []
            if is_admin and not target_user_id:
                # Admin exporting all data unfiltered
                return list(db[collection_name].find())
            if not is_admin:
                # Regular user exports their own data for user-owned collections
                if collection_name in user_owned_collections:
                    field = user_owned_collections[collection_name]
                    return list(db[collection_name].find({field: ObjectId(current_user_id)}))
                # Skips admin-only collections for regular users
                elif collection_name in admin_only_collections:
                    return []
                else:
                    # Public collections accessible by all users
                    return list(db[collection_name].find())
            # Default fallback - empty
            return []

        if format_type == "json":
            full_data = {}
            for collection_name in collections_to_export:
                docs = get_filtered_docs(collection_name)
                full_data[collection_name] = json.loads(dumps(docs))
            return JsonResponse(full_data, safe=False, json_dumps_params={'indent': 2})

        elif format_type == "csv":
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for collection_name in collections_to_export:
                    docs = get_filtered_docs(collection_name)
                    if not docs:
                        continue
                    csv_buffer = io.StringIO()
                    writer = csv.writer(csv_buffer)
                    headers = sorted({key for doc in docs for key in doc.keys()})
                    writer.writerow(headers)
                    for doc in docs:
                        row = [doc.get(key, "") for key in headers]
                        writer.writerow(row)
                    zip_file.writestr(f"{collection_name}.csv", csv_buffer.getvalue())
            zip_buffer.seek(0)
            response = HttpResponse(zip_buffer, content_type='application/zip')
            response['Content-Disposition'] = 'attachment; filename="user_export.zip"'
            return response

        else:
            return JsonResponse({"error": "Unsupported format type"}, status=400)

    except Exception as e:
        logger.error(f"Error in export_data: {str(e)}", exc_info=True)
        return JsonResponse({"error": "An error occurred while exporting data"}, status=500)