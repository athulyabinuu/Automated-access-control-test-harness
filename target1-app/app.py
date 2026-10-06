from flask import Flask, jsonify, request, render_template, redirect
import jwt
from functools import wraps
import os

app = Flask(__name__)

SECRET_KEY = "access-control-test-secret"


# ============================================================
# TEST USERS
# ============================================================

users = {
    "admin": {
        "id": 1,
        "username": "admin",
        "password": os.getenv("TARGET1_ADMIN_PASSWORD", "admin123"),
        "role": "admin"
    },

    "user1": {
        "id": 2,
        "username": "user1",
        "password": os.getenv("TARGET1_USER1_PASSWORD", "user123"),
        "role": "user"
    },

    "user2": {
        "id": 3,
        "username": "user2",
        "password": os.getenv("TARGET1_USER2_PASSWORD", "user456"),
        "role": "user"
    }
}


# ============================================================
# HOME
# ============================================================

@app.route("/", methods=["GET"])
def home():
    if "text/html" in request.headers.get("Accept", "") and "python-requests" not in request.headers.get("User-Agent", ""):
        return redirect("/login")

    return jsonify({
        "message": "Access Control Test Harness - Target API",
        "status": "running"
    }), 200


# ============================================================
# LOGIN
# ============================================================

@app.route("/api/login", methods=["POST"])
def login():

    data = request.get_json(silent=True) or {}

    username = data.get("username")
    password = data.get("password")

    user = users.get(username)

    if not user or user["password"] != password:
        return jsonify({
            "error": "Invalid username or password"
        }), 401

    token = jwt.encode(
        {
            "user_id": user["id"],
            "username": user["username"],
            "role": user["role"]
        },
        SECRET_KEY,
        algorithm="HS256"
    )

    return jsonify({
        "message": "Login successful",
        "token": token
    }), 200


# ============================================================
# JWT AUTHENTICATION
# ============================================================

def token_required(f):

    @wraps(f)
    def decorated(*args, **kwargs):

        token = request.headers.get("Authorization")

        if not token:
            return jsonify({
                "error": "Authorization token required"
            }), 401

        try:

            if token.startswith("Bearer "):
                token = token[7:]

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

        return f(*args, **kwargs)

    return decorated


# ============================================================
# PRODUCTS
# ============================================================

@app.route("/api/products", methods=["GET"])
def products():

    return jsonify({
        "products": [
            {
                "id": 1,
                "name": "Laptop"
            },
            {
                "id": 2,
                "name": "Keyboard"
            },
            {
                "id": 3,
                "name": "Mouse"
            }
        ]
    }), 200


# ============================================================
# CURRENT USER
# ============================================================

@app.route("/api/me", methods=["GET"])
@token_required
def me():

    return jsonify({
        "id": request.user["user_id"],
        "username": request.user["username"],
        "role": request.user["role"]
    }), 200


# ============================================================
# TEST USER PROFILES
# ============================================================

profiles = {
    1: {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com"
    },

    2: {
        "id": 2,
        "username": "user1",
        "email": "user1@example.com"
    },

    3: {
        "id": 3,
        "username": "user2",
        "email": "user2@example.com"
    }
}


# ============================================================
# TEST ORDERS
# ============================================================

orders = {
    101: {
        "id": 101,
        "user_id": 2,
        "item": "Laptop"
    },

    102: {
        "id": 102,
        "user_id": 3,
        "item": "Keyboard"
    }
}


# ============================================================
# GET USER PROFILE
# ============================================================

@app.route("/api/users/<int:user_id>", methods=["GET"])
@token_required
def get_user_profile(user_id):

    profile = profiles.get(user_id)

    if not profile:
        return jsonify({
            "error": "User not found"
        }), 404

    # Admin can access any user.
    if request.user["role"] == "admin":
        return jsonify(profile), 200

    # Normal user can access only their own profile.
    if request.user["user_id"] != user_id:
        return jsonify({
            "error": "Access denied"
        }), 403

    return jsonify(profile), 200


# ============================================================
# PATCH USER PROFILE
# ============================================================

@app.route("/api/users/<int:user_id>", methods=["PATCH"])
@token_required
def update_user_profile(user_id):

    profile = profiles.get(user_id)

    if not profile:
        return jsonify({
            "error": "User not found"
        }), 404

    # Admin can update any user.
    if request.user["role"] == "admin":
        pass

    # Normal user can update only their own profile.
    elif request.user["user_id"] != user_id:
        return jsonify({
            "error": "Access denied"
        }), 403

    data = request.get_json(silent=True) or {}

    if "username" in data:
        profile["username"] = data["username"]

    if "email" in data:
        profile["email"] = data["email"]

    return jsonify({
        "message": "Profile updated successfully",
        "user": profile
    }), 200


# ============================================================
# GET USER ORDER
# ============================================================

@app.route("/api/orders/<int:order_id>", methods=["GET"])
@token_required
def get_order(order_id):

    order = orders.get(order_id)

    if not order:
        return jsonify({
            "error": "Order not found"
        }), 404

    # Admin can access any order.
    if request.user["role"] == "admin":
        return jsonify(order), 200

    # Normal user can access only their own order.
    if request.user["user_id"] != order["user_id"]:
        return jsonify({
            "error": "Access denied"
        }), 403

    return jsonify(order), 200


# ============================================================
# ADMIN - VIEW ALL USERS
# ============================================================

@app.route("/api/admin/users", methods=["GET"])
@token_required
def admin_users():

    if request.user["role"] != "admin":
        return jsonify({
            "error": "Admin access required"
        }), 403

    return jsonify({
        "users": list(profiles.values())
    }), 200


# ============================================================
# ADMIN - DELETE USER
# ============================================================

@app.route("/api/admin/users/<int:user_id>", methods=["DELETE"])
@token_required
def delete_admin_user(user_id):

    if request.user["role"] != "admin":
        return jsonify({
            "error": "Admin access required"
        }), 403

    profile = profiles.get(user_id)

    if not profile:
        return jsonify({
            "error": "User not found"
        }), 404

    if user_id == 1:
        return jsonify({
            "error": "Cannot delete admin user"
        }), 403

    # --------------------------------------------------------
    # TEST-HARNESS BEHAVIOUR
    #
    # Return successful deletion without permanently removing
    # the in-memory test profile.
    #
    # This keeps later tests independent.
    # --------------------------------------------------------

    return jsonify({
        "message": "User deleted successfully",
        "user_id": user_id
    }), 200


# ============================================================
# ADMIN - VIEW SINGLE USER
# ============================================================

@app.route("/api/admin/users/<int:user_id>", methods=["GET"])
@token_required
def admin_user(user_id):

    if request.user["role"] != "admin":
        return jsonify({
            "error": "Admin access required"
        }), 403

    profile = profiles.get(user_id)

    if not profile:
        return jsonify({
            "error": "User not found"
        }), 404

    return jsonify(profile), 200


# ============================================================
# ADMIN STATISTICS
# ============================================================

@app.route("/api/admin/stats", methods=["GET"])
@token_required
def admin_stats():

    if request.user["role"] != "admin":
        return jsonify({
            "error": "Admin access required"
        }), 403

    return jsonify({
        "total_users": len(profiles),
        "total_orders": len(orders),
        "total_products": 3
    }), 200


# ============================================================
# FRONTEND WEB ROUTES (SecureLab Platform)
# ============================================================

@app.route("/login", methods=["GET"])
def web_login():
    return render_template("login.html")


@app.route("/dashboard", methods=["GET"])
def web_dashboard():
    return render_template("dashboard.html")


@app.route("/products", methods=["GET"])
def web_products():
    return render_template("products.html")


@app.route("/profile", methods=["GET"])
def web_profile():
    return render_template("profile.html")


@app.route("/orders", methods=["GET"])
def web_orders():
    return render_template("orders.html")


@app.route("/users", methods=["GET"])
def web_users():
    return render_template("users.html")


@app.route("/admin", methods=["GET"])
def web_admin():
    return render_template("admin.html")


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )