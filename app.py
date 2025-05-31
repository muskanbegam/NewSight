from flask import Flask, jsonify, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float
from geopy.geocoders import Nominatim
from geopy.distance import geodesic


def get_lat_long(location_name):
    geolocator = Nominatim(user_agent="my_app", timeout=20)  # Increased timeout
    location = geolocator.geocode(location_name)
    if location:
        return (location.latitude, location.longitude)
    else:
        return None


app = Flask(__name__)

class Base(DeclarativeBase):
    pass

app.config['SQLALCHEMY_BINDS'] = {
    'content': 'sqlite:///content-collection.db',
    'users': 'sqlite:///users.db'
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Content(db.Model):
    __bind_key__ = 'content'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    heading: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subheading: Mapped[str] = mapped_column(String(250), nullable=False)
    content: Mapped[str] = mapped_column(String(427), nullable=False)
    link: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str] = mapped_column(String, nullable=False)
    image: Mapped[str] = mapped_column(String, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=True)

class Users(db.Model):
    __bind_key__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)


@app.route('/', methods=['GET', 'POST', 'HEAD'])
def home():
    user_location = request.form.get('location')
    if user_location:
        user_coords = get_lat_long(user_location)
        if user_coords:
            content_db = db.session.query(Content).all()
            content_with_distance = []
            for content in content_db:
                if content.latitude and content.longitude:
                    content_coords = (content.latitude, content.longitude)
                    distance = geodesic(user_coords, content_coords).kilometers
                    content_with_distance.append((content, distance))

            sorted_content = sorted(content_with_distance, key=lambda x: x[1], reverse=True)
            sorted_content_only = [c[0] for c in sorted_content]

            return render_template("index.html", data=sorted_content_only, length=len(sorted_content_only), so=0)

    # fallback if no user location or error
    content_db = db.session.query(Content).all()
    return render_template("index.html", data=content_db, length=len(content_db), so=0)


@app.route("/loggedIn/<int:so>")
def loggedIn(so):
    content_db = db.session.query(Content).all()
    length = len(content_db)
    if so == 1:
        return render_template("index.html", so=so, data=content_db, length=length)
    else:
        return redirect(url_for("home"))


@app.route("/login", methods=["GET", "POST", 'HEAD'])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if email == "admin@gmail.com" and password == "(Adminnewsight.1)":
            content_db = db.session.query(Content).all()
            return render_template("admin-dashboard.html", data=content_db, length=len(content_db))

        user = db.session.query(Users).filter_by(email=email).first()
        if user and user.password == password:
            return redirect(url_for("loggedIn", so=1))

        return render_template("login.html", error="Invalid credentials.")

    return render_template("login.html")


@app.route("/admin-dashboard")
def admin_dashboard():
    content_db = db.session.query(Content).all()
    return render_template("admin-dashboard.html", data=content_db, length=len(content_db))


@app.route("/signup", methods=["GET", "POST", 'HEAD'])
def signup():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        new_user = Users(name=name, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("login"))

    return render_template("signup.html")


@app.route('/new-post', methods=["GET", "POST", 'HEAD'])
def new_post():
    if request.method == "POST":
        image = request.form.get("image")
        heading = request.form.get("heading")
        subheading = request.form.get("subheading")
        content_text = request.form.get("content")
        link = request.form.get("link")
        location = request.form.get("location")

        coords = get_lat_long(location)
        latitude, longitude = coords if coords else (None, None)

        new_post = Content(
            heading=heading,
            subheading=subheading,
            content=content_text,
            link=link,
            location=location,
            image=image,
            latitude=latitude,
            longitude=longitude
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("home"))

    return render_template("new-post.html")


@app.route("/delete/<int:id>")
def delete(id):
    content_to_delete = db.session.execute(db.select(Content).where(Content.id == id)).scalar()
    db.session.delete(content_to_delete)
    db.session.commit()
    content_db = db.session.query(Content).all()
    return render_template("admin-dashboard.html", data=content_db, length=len(content_db))


if __name__ == '__main__':
    with app.app_context():
        # Create tables for each bind separately
        engine_content = db.engines['content']
        Content.metadata.create_all(engine_content)

        engine_users = db.engines['users']
        Users.metadata.create_all(engine_users)

    app.run(debug=False)
