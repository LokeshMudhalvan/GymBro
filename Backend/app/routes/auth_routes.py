from flask import Blueprint, jsonify, request
from app import db
from app.model import Users
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/register", methods=["POST"])
def register_user():
    try:
        data = request.get_json()
        email_data = data.get("email")
        username = data.get("username")
        password = data.get("password")

        if not email_data or not username or password:
            print(f"An error occured while trying to register, Username, Email and Password are required fields")
            return jsonify({"error": "Missing fields. Make sure, you have entered all the required fields(Username, Email, Password)"}), 404
        
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        if Users.query.filter_by(email=email_data).first():
            print("An error occured while trying to register user. User already exists")
            return jsonify({"error": "User already exists. Try logging in"}), 404
    
        user = Users(
            name = username,
            email = email_data,
            password_hash = hashed_password
        )

        db.session.add(user)
        db.session.commit()

        return jsonify({"message": "User registered successfully"}), 200
    
    except Exception as e:
        print(f'An error occured while trying to register user: {str(e)}')
        return jsonify({"error": "An error occured while trying to register user. Try agian later"}), 500
    
@auth_bp.route("/login", methods=["POST"])
def login_user():
    try:
        data = request.get_json()
        email_data = data.get("email")
        password = data.get("password")

        if not email_data or not password:
            print("An error occured during login. Email and Password are mandatory fields")
            return jsonify({"error": "Login Failed. Make sure you have filled in the mandatory fields (Email and Password)"}), 404
        
        if not Users.query.filter_by(email=email_data).first():
            print("Invalid request. User does not exist")
            return jsonify({"error": "Invalid request. User does not exist. Please register first."})
        
        user = Users.query.filter_by(email=email_data).first()

        if check_password_hash(user.password_hash, password):
            access_token = create_access_token(user.user_id)
            return jsonify({
                "message": "Login Successful",
                "token": access_token
            }), 200
        
        return jsonify({"error": "Invalid Credentials"}), 404
    
    except Exception as e:
        print(f"An error occured while trying to login: {str(e)}")