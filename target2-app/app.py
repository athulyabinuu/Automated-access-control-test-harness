from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from functools import wraps
import os
import jwt
from datetime import datetime, timedelta

app = Flask(__name__)

app.secret_key = "target2-session-secret"

SECRET_KEY = "target2-jwt-secret"


# ============================================================
# TEST USERS
# ============================================================

users = {
    "admin": {
        "id": 1,
        "username": "admin",
        "password": os.getenv("TARGET2_ADMIN_PASSWORD", "admin123"),
        "role": "admin",
        "email": "admin@target2.local"
    },

    "user1": {
        "id": 2,
        "username": "user1",
        "password": os.getenv("TARGET2_USER_PASSWORD", "user123"),
        "role": "user",
        "email": "user1@target2.local"
    },

    "user2": {
        "id": 3,
        "username": "user2",
        "password": os.getenv("TARGET2_USER_PASSWORD", "user123"),
        "role": "user",
        "email": "user2@target2.local"
    }
}


# ============================================================
# USER PROFILES
# ============================================================

profiles = {
    1: {
        "id": 1,
        "username": "admin",
        "email": "admin@target2.local"
    },

    2: {
        "id": 2,
        "username": "user1",
        "email": "user1@target2.local"
    },

    3: {
        "id": 3,
        "username": "user2",
        "email": "user2@target2.local"
    }
}


# ============================================================
# ORDERS
# ============================================================

orders = {
    101: {
        "id": 101,
        "user_id": 2,
        "item": "Professional Laptop",
        "amount": 85000,
        "status": "Delivered"
    },

    102: {
        "id": 102,
        "user_id": 3,
        "item": "Mechanical Keyboard",
        "amount": 7500,
        "status": "Processing"
    }
}


# ============================================================
# PRODUCTS
# ============================================================

products = [
    {
        "id": 1,
        "name": "Professional Laptop",
        "price": 85000
    },

    {
        "id": 2,
        "name": "Mechanical Keyboard",
        "price": 7500
    },

    {
        "id": 3,
        "name": "Wireless Mouse",
        "price": 2500
    }
]


# ============================================================
# JWT TOKEN CREATION
# ============================================================

def create_token(user):

    return jwt.encode(
        {
            "user_id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "exp": datetime.utcnow() + timedelta(hours=2)
        },
        SECRET_KEY,
        algorithm="HS256"
    )


# ============================================================
# JWT AUTHENTICATION
# ============================================================

def token_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        authorization = request.headers.get("Authorization")

        if not authorization:

            return jsonify({
                "error": "Authorization token required"
            }), 401

        token = authorization.replace("Bearer ", "")

        try:

            decoded = jwt.decode(
                token,
                SECRET_KEY,
                algorithms=["HS256"]
            )

            request.user = decoded

        except jwt.InvalidTokenError:

            return jsonify({
                "error": "Invalid token"
            }), 401

        return function(*args, **kwargs)

    return wrapper


# ============================================================
# WEB LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def web_login():

    error = None

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        user = users.get(username)

        if not user or user["password"] != password:

            error = "Invalid username or password"

        else:

            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            return redirect(url_for("dashboard"))

    return render_template(
        "login.html",
        error=error
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("index"))


# ============================================================
# WEB AUTHENTICATION
# ============================================================

def web_login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:

            return redirect(url_for("web_login"))

        return function(*args, **kwargs)

    return wrapper


# ============================================================
# HOME PAGE
# ============================================================

@app.route("/")
def index():

    return render_template("index.html")


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
@web_login_required
def dashboard():

    return render_template(
        "dashboard.html",
        username=session["username"],
        role=session["role"]
    )


# ============================================================
# PROFILE PAGE
# ============================================================

@app.route("/profile")
@web_login_required
def profile():

    profile_data = profiles.get(
        session["user_id"]
    )

    return render_template(
        "profile.html",
        profile=profile_data
    )


# ============================================================
# ORDERS PAGE
# ============================================================

@app.route("/orders")
@web_login_required
def orders_page():

    if session["role"] == "admin":

        user_orders = list(orders.values())

    else:

        user_orders = [
            order
            for order in orders.values()
            if order["user_id"] == session["user_id"]
        ]

    return render_template(
        "orders.html",
        orders=user_orders
    )


# ============================================================
# ADMIN USERS PAGE
# ============================================================

@app.route("/admin/users")
@web_login_required
def admin_users_page():

    if session["role"] != "admin":

        return "Access denied", 403

    return render_template(
        "admin_users.html",
        users=profiles.values()
    )


# ============================================================
# ADMIN STATISTICS PAGE
# ============================================================
@app.route("/admin/stats")
def admin_stats():

    if "username" not in session:
        return redirect("/login")

    # INTENTIONALLY VULNERABLE:
    # Missing role/privilege check allows ordinary authenticated
    # users to access the admin statistics page.

    total_users = len(users)
    total_orders = len(orders)
    total_products = len(products)

    return render_template(
        "admin_stats.html",
        total_users=total_users,
        total_orders=total_orders,
        total_products=total_products
    )


# ============================================================
# API LOGIN
# ============================================================

@app.route("/api/login", methods=["POST"])
def api_login():

    data = request.get_json(silent=True) or {}

    username = data.get("username")
    password = data.get("password")

    user = users.get(username)

    if not user or user["password"] != password:

        return jsonify({
            "error": "Invalid username or password"
        }), 401

    return jsonify({
        "message": "Login successful",
        "token": create_token(user)
    }), 200


# ============================================================
# API PRODUCTS
# ============================================================

@app.route("/api/products", methods=["GET"])
def api_products():

    return jsonify({
        "products": products
    }), 200


# ============================================================
# API CURRENT USER
# ============================================================

@app.route("/api/me", methods=["GET"])
@token_required
def api_me():

    return jsonify({
        "id": request.user["user_id"],
        "username": request.user["username"],
        "role": request.user["role"]
    }), 200


# ============================================================
# API USER PROFILE
# ============================================================

@app.route("/api/users/<int:user_id>", methods=["GET"])
@token_required
def api_user_profile(user_id):

    profile_data = profiles.get(user_id)

    if not profile_data:

        return jsonify({
            "error": "User not found"
        }), 404

    # Admin can access any profile.
    if request.user["role"] == "admin":

        return jsonify(profile_data), 200

    # Normal users can access only their own profile.
    if request.user["user_id"] != user_id:

        return jsonify({
            "error": "Access denied"
        }), 403

    return jsonify(profile_data), 200


# ============================================================
# API UPDATE USER PROFILE
# ============================================================

@app.route("/api/users/<int:user_id>", methods=["PATCH"])
@token_required
def api_update_profile(user_id):

    profile_data = profiles.get(user_id)

    if not profile_data:

        return jsonify({
            "error": "User not found"
        }), 404

    # Admin can update any profile.
    if request.user["role"] == "admin":

        pass

    # Normal users can update only their own profile.
    elif request.user["user_id"] != user_id:

        return jsonify({
            "error": "Access denied"
        }), 403

    data = request.get_json(silent=True) or {}

    if "email" in data:

        profile_data["email"] = data["email"]

    return jsonify({
        "message": "Profile updated",
        "user": profile_data
    }), 200


# ============================================================
# API ORDERS
# ============================================================

@app.route("/api/orders/<int:order_id>", methods=["GET"])
@token_required
def api_order(order_id):

    order = orders.get(order_id)

    if not order:

        return jsonify({
            "error": "Order not found"
        }), 404

    # Admin can access any order.
    if request.user["role"] == "admin":

        return jsonify(order), 200

    # Normal users can access only their own orders.
    if request.user["user_id"] != order["user_id"]:

        return jsonify({
            "error": "Access denied"
        }), 403

    return jsonify(order), 200


# ============================================================
# ADMIN API - VIEW USERS
# ============================================================

@app.route("/api/admin/users", methods=["GET"])
@token_required
def api_admin_users():

    if request.user["role"] != "admin":

        return jsonify({
            "error": "Admin access required"
        }), 403

    return jsonify({
        "users": list(profiles.values())
    }), 200


# ============================================================
# ADMIN API - DELETE USER
# ============================================================

@app.route("/api/admin/users/<int:user_id>", methods=["DELETE"])
@token_required
def api_delete_user(user_id):

    if request.user["role"] != "admin":

        return jsonify({
            "error": "Admin access required"
        }), 403

    if user_id not in profiles:

        return jsonify({
            "error": "User not found"
        }), 404

    if user_id == 1:

        return jsonify({
            "error": "Cannot delete administrator"
        }), 403

    return jsonify({
        "message": "User deleted successfully",
        "user_id": user_id
    }), 200


# ============================================================
# ADMIN API - STATISTICS
# ============================================================

@app.route("/api/admin/stats", methods=["GET"])
@token_required
def api_admin_stats():

    if str(request.user.get("role", "")).upper() != "ADMIN":
        return jsonify({
            "error": "Admin access required"
        }), 403

    return jsonify({
        "total_users": 2,
        "total_orders": 2,
        "total_products": 3,
        "message": "Administrator statistics"
    }), 200

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5001,
        debug=True
    )
