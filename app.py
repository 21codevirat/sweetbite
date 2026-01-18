from sqlalchemy import func
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from flask import send_file
import io
from flask import Flask, render_template, request, redirect, session
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template
from flask import request   # make sure this import exists

print(">>> THIS IS MY SWEETBITE APP <<<")

app = Flask(__name__)
app.secret_key = "sweetbite_secret_key"
ADMIN_EMAIL = "admin@sweetbite.com"
ADMIN_PASSWORD = "Virat@213111"


app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Virat%40213111@localhost:5432/sweetbite1_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    price = db.Column(db.Integer)
    image = db.Column(db.String(255))   # ✅ ADD THIS LINE


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(100))
    user_id = db.Column(db.Integer)
    total_price = db.Column(db.Integer)
    status = db.Column(db.String(50), default="Placed")




class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer)
    product_name = db.Column(db.String(100))
    price = db.Column(db.Integer)
    quantity = db.Column(db.Integer)


def admin_required():
    if not session.get("admin_logged_in"):
        return False
    return True


# HOME
@app.route("/")
def home():
    return render_template("index.html")


# PRODUCTS
@app.route("/products")
def products():
    products = Product.query.all()
    print("DEBUG PRODUCTS:", products)
    return render_template("products.html", products=products)



# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect("/admin")
        else:
            return "Invalid admin credentials"

    return render_template("login.html")


# SIGNUP
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return "User already exists"

        new_user = User(name=name, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()

        session["user_logged_in"] = True
        session["user_name"] = name

        return redirect("/")

    return render_template("signup.html")

@app.route("/user-login", methods=["GET", "POST"])
def user_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email, password=password).first()

        if user:
            session["user_logged_in"] = True
            session["user_name"] = user.name
            return redirect("/")
        else:
            return "Invalid user credentials"

    return render_template("user_login.html")

@app.route("/user-logout")
def user_logout():
    session.pop("user_logged_in", None)
    session.pop("user_name", None)
    return redirect("/")



# ADMIN DASHBOARD
@app.route("/admin")
def admin_dashboard():
    orders = Order.query.all()
    return render_template("admin_dashboard.html", orders=orders)


@app.route("/admin/analytics")
def admin_analytics():
    if not admin_required():
        return redirect("/login")

    total_orders = Order.query.count()
    total_revenue = db.session.query(db.func.sum(Order.total_price
)).scalar() or 0
    total_items = db.session.query(db.func.sum(OrderItem.quantity)).scalar() or 0

    return render_template(
        "admin_analytics.html",
        total_orders=total_orders,
        total_revenue=total_revenue,
        total_items=total_items
    )


# ADD PRODUCT
@app.route("/admin/add-product", methods=["GET", "POST"])
def add_product():
    if not admin_required():
        return redirect("/login")

    if request.method == "POST":
        name = request.form["name"]
        price = request.form["price"]
        new_product = Product(name=name, price=price)
        db.session.add(new_product)
        db.session.commit()
        return redirect("/products")

    return render_template("add_product.html")


@app.route("/admin/edit-product/<int:id>", methods=["GET", "POST"])
def edit_product(id):
    if not admin_required():
        return redirect("/login")

    product = Product.query.get(id)

    if request.method == "POST":
        product.name = request.form["name"]
        product.price = request.form["price"]
        db.session.commit()
        return redirect("/products")

    return render_template("edit_product.html", product=product)



@app.route("/admin/delete-product/<int:id>", methods=["POST"])
def delete_product(id):
    if not admin_required():
        return redirect("/login")

    product = Product.query.get(id)
    db.session.delete(product)
    db.session.commit()
    return redirect("/products")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/add-to-cart/<int:id>", methods=["POST"])
def add_to_cart(id):
    product = Product.query.get(id)

    if not product:
        return redirect("/products")

    cart = session.get("cart", [])

    for item in cart:
        if item["name"] == product.name:
            item["qty"] += 1
            session["cart"] = cart
            return redirect("/products")

    cart.append({
        "name": product.name,
        "price": product.price,
        "qty": 1
    })

    session["cart"] = cart
    return redirect("/products")

@app.route("/cart")
def cart():
    cart = session.get("cart", [])
    total = sum(item["price"] * item["qty"] for item in cart)
    return render_template("cart.html", cart=cart, total=total)

@app.route("/remove-from-cart/<int:index>")
def remove_from_cart(index):
    cart = session.get("cart", [])
    if index < len(cart):
        cart.pop(index)
    session["cart"] = cart
    return redirect("/cart")

@app.route("/place-order")
def place_order():
    if not session.get("user_logged_in"):
        return redirect("/user-login")

    cart = session.get("cart", [])
    if not cart:
        return redirect("/cart")

    total = sum(item["price"] * item["qty"] for item in cart)

    order = Order(
        user_name=session.get("user_name"),
        total_amount=total
    )
    db.session.add(order)
    db.session.commit()

    for item in cart:
        order_item = OrderItem(
            order_id=order.id,
            product_name=item["name"],
            price=item["price"],
            quantity=item["qty"]
        )
        db.session.add(order_item)

    db.session.commit()
    session.pop("cart")

    return redirect(f"/invoice/{order.id}")


@app.route("/invoice/<int:order_id>")
def generate_invoice(order_id):
    order = Order.query.get(order_id)
    items = OrderItem.query.filter_by(order_id=order_id).all()

    if not order:
        return "Order not found"

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # 🔹 HEADER
    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(50, height - 50, "SWEETBITE BAKERY")

    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, height - 70, "Fresh Cakes | Pastries | Desserts")
    pdf.drawString(50, height - 85, "Contact: +91 98765 43210")
    pdf.drawString(50, height - 100, "Address: SweetBite Bakery, India")

    pdf.line(50, height - 110, width - 50, height - 110)

    # 🔹 INVOICE INFO
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, height - 140, f"Invoice No: {order.id}")
    pdf.drawString(50, height - 160, f"Customer Name: {order.user_name}")

    # 🔹 TABLE HEADER
    y = height - 200
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(50, y, "Product")
    pdf.drawString(300, y, "Price")
    pdf.drawString(380, y, "Qty")
    pdf.drawString(450, y, "Total")

    pdf.line(50, y - 5, width - 50, y - 5)

    # 🔹 TABLE DATA
    pdf.setFont("Helvetica", 11)
    y -= 25
    grand_total = 0

    for item in items:
        item_total = item.price * item.quantity
        grand_total += item_total

        pdf.drawString(50, y, item.product_name)
        pdf.drawString(300, y, f"₹ {item.price}")
        pdf.drawString(380, y, str(item.quantity))
        pdf.drawString(450, y, f"₹ {item_total}")
        y -= 20

    pdf.line(50, y - 5, width - 50, y - 5)

    # 🔹 TOTAL SECTION
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(350, y - 30, "Grand Total:")
    pdf.drawString(450, y - 30, f"₹ {grand_total}")

    # 🔹 FOOTER
    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, 80, "Thank you for ordering from SWEETBITE!")
    pdf.drawString(50, 65, "We hope to serve you again soon.")

    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"SweetBite_Invoice_{order.id}.pdf",
        mimetype="application/pdf"
    )

@app.route("/track-order/<int:order_id>")
def track_order(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template("track_order.html", order=order)

@app.route("/admin/update-order/<int:order_id>/<status>")
def update_order_status(order_id, status):
    order = Order.query.get_or_404(order_id)
    order.status = status
    db.session.commit()
    return redirect("/admin")


with app.app_context():
    db.create_all()


# 🚨 DO NOT WRITE ANY CODE BELOW THIS 🚨
if __name__ == "__main__":
    app.run(debug=True)
    