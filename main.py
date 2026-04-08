import os
from datetime import date
from flask_mail import Mail, Message
from smtplib import SMTPException
from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from sqlalchemy import Integer, String, Text, ForeignKey, Boolean, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from werkzeug.security import generate_password_hash, check_password_hash
from forms import CreatePostForm, LoginForm, RegisterForm, ContactForm, CommentForm
from flask_wtf.csrf import CSRFError
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
#Configure mail service
app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER")
app.config["MAIL_PORT"] = os.environ.get("MAIL_PORT")
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USE_SSL"] = False
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_USERNAME")

Bootstrap5(app)

#Initalize DB
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
uri = os.environ.get("DATABASE_URL", "sqlite:///travel-blog-posts.db")
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = uri
db.init_app(app)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(250), nullable=False)
    last_name: Mapped[str] = mapped_column(String(250), nullable=False)
    email: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(250), nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False)
    posts = relationship("BlogPost", back_populates="user")
    comments = relationship("Comment", back_populates="user")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    location: Mapped[str] = mapped_column(String(250), nullable=False)
    num_times_visited: Mapped[int] = mapped_column(Integer, nullable=False)
    visit_again: Mapped[bool] = mapped_column(Boolean, nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    rating: Mapped[str] = mapped_column(String(250), nullable=False)
    img_url: Mapped[str] = mapped_column(Text, nullable=False)
    user = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post")

    def calc_comments_count(self):
        return len(self.comments)

class Comment(db.Model):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id = mapped_column(ForeignKey("users.id"))
    post_id = mapped_column(ForeignKey("blog_posts.id"))
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    user = relationship("User", back_populates="comments")
    post = relationship("BlogPost", back_populates="comments")


class Contact(db.Model):
    __tablename__ = "contact_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    email: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)


with app.app_context():
    db.create_all()


#Configure Flask Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)

#Flask Mail
mail = Mail(app)

#Generate token for verification email
def generate_verification_token(user_id):
    auth_s = URLSafeTimedSerializer(app.config["SECRET_KEY"])
    token = auth_s.dumps(user_id, salt="verify-email")
    return token

@app.errorhandler(CSRFError)
def handle_csrf_error():
    flash("Your session has expired. Please log in again.", "error")
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method="pbkdf2", salt_length=8)
        new_user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            password=hashed_password,
            is_verified=False
        )
        db.session.add(new_user)
        #save new user to db
        try:
            db.session.commit()
        except IntegrityError:
            #If user email exists:
            flash("Email already exists. Please login in.", "error")
            return redirect(url_for("login"))
        else:
            #ELSE send confirmation email
            #IF received, redirect to login page
            #IF not received, render verification page

            #Build confirmation URL and include in the verification email
            token = generate_verification_token(new_user.id)
            verify_url = url_for("verify_email", token=token, _external=True)
            verification_msg = Message(
                f"Verify your email",
                recipients=[new_user.email],
                html=f"<h4>Thank you for registering!</h4>"
                     f"<p>Click the link below to verify your account:<br><a href='{verify_url}'><strong>Verify my account</strong></a></p>"
                     f"<p><em>This link will expire in 24 hours.</em></p>"
            )
            try:
                mail.send(verification_msg)
            except SMTPException:
                flash("Failed to send confirmation email. Please try again.", "error")
                return render_template("verify-email.html", user=new_user)
            else:
                return render_template("verify-email.html", user=new_user)

    return render_template("register.html", form=form)

@app.route("/register/verify/<int:user_id>")
def resend_verification_email(user_id):
    #IF resend button is clicked, do this:
    user = db.session.get(User, user_id)
    token = generate_verification_token(user.id)
    verify_url = url_for("verify_email", token=token, _external=True)
    verification_msg = Message(
        f"Verify your email",
        recipients=[user.email],
        html=f"<h4>Thank you for registering!</h4>"
             f"<p>Click the link below to verify your account:<br><a href='{verify_url}'><strong>Verify my account</strong></a></p>"
             f"<p><em>This link will expire in 24 hours.</em></p>"
    )
    try:
        mail.send(verification_msg)
    except SMTPException:
        flash("Failed to send confirmation email. Please try again.", "error")
        return render_template("verify-email.html", user=user)
    else:
        flash("Confirmation email resent.", "success")
        return render_template("verify-email.html", user=user)


@app.route("/verify/<token>")
def verify_email(token):
    auth_s = URLSafeTimedSerializer(app.config["SECRET_KEY"])
    try:
        user_id = auth_s.loads(token, salt="verify-email", max_age=86400)
    except SignatureExpired:
        flash("Verification link has expired.", "error")
        return redirect(url_for("login"))
    except BadSignature:
        flash("Invalid verification link.", "error")
        return redirect(url_for("login"))
    else:
        user = db.session.get(User, user_id)
        user.is_verified = True
        db.session.commit()
        flash("Email successfully verified. You can now log in.", "success")
        return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.execute(db.select(User).where(User.email == form.email.data)).scalar()
        if user:
            if user.is_verified:
                stored_password = user.password
                if check_password_hash(stored_password, form.password.data):
                    login_user(user)
                    return redirect(url_for("get_all_posts"))
                else:
                    flash("Invalid password. Please try again.", "error")
            else:
                flash("Please verify your email before logging in.", "error")
                # print(user.id)
                return render_template("login.html", form=form, unverified_user_id=user.id)
        else:
            flash("That email does not exist. Want to sign up?", "error")
    return render_template("login.html", form=form)


@app.route("/logout")
def logout():
    logout_user()
    flash("You have successfully logged out.", "success")
    return redirect(url_for("login"))


@app.route("/")
def get_all_posts():
    all_posts = db.session.execute(db.select(BlogPost).order_by(desc(BlogPost.id))).scalars().all()
    return render_template("index.html", posts=all_posts)

@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def get_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    comments = db.session.execute(db.select(Comment).where(Comment.post == post).order_by(desc(Comment.id))).scalars().all()

    form = CommentForm()
    if form.validate_on_submit():
        if current_user.is_authenticated:
            new_comment = Comment(
                comment=form.comment.data,
                date=date.today().strftime("%B %d"),
                user=current_user,
                post=post
            )
            db.session.add(new_comment)
            db.session.commit()

            return redirect(url_for("get_post", post_id=post.id))
        else:
            flash("Please log in.", "error")
            return redirect(url_for("login"))

    return render_template("post.html", post=post, form=form, comments=comments)

@app.route("/add-post", methods=["GET", "POST"])
@login_required
def create_post():
    form = CreatePostForm()

    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            location=form.location.data,
            num_times_visited=form.num_times_visited.data,
            visit_again=form.visit_again.data,
            date=date.today().strftime("%B %d, %Y"),
            body=form.body.data,
            rating=form.rating.data,
            img_url=form.img_url.data,
            user=current_user
        )
        db.session.add(new_post)
        db.session.commit()
        post_id = db.session.execute(db.select(BlogPost).where(BlogPost.title == form.title.data)).scalar().id
        return redirect(url_for("get_post", post_id=post_id))

    return render_template("add-post.html", form=form)

@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@login_required
def update_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title = post.title,
        subtitle = post.subtitle,
        location = post.location,
        num_times_visited = post.num_times_visited,
        visit_again = post.visit_again,
        body = post.body,
        rating = post.rating,
        img_url = post.img_url,
        user=current_user
    )

    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.location = edit_form.location.data
        post.num_times_visited = edit_form.num_times_visited.data
        post.visit_again = edit_form.visit_again.data
        post.body = edit_form.body.data
        post.rating = edit_form.rating.data
        post.img_url = edit_form.img_url.data
        post.user = current_user

        db.session.commit()
        return redirect(url_for("get_post", post_id=post.id))

    return render_template("add-post.html", form=edit_form, is_edit=True)

@app.route("/delete-post/<int:post_id>")
@login_required
def delete_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    db.session.delete(post)
    db.session.commit()
    return redirect(url_for("get_all_posts"))

@app.route("/delete-comment/<int:comment_id>")
@login_required
def delete_comment(comment_id):
    comment = db.get_or_404(Comment, comment_id)
    db.session.delete(comment)
    db.session.commit()
    return redirect(url_for("get_post", post_id=comment.post_id))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    form = ContactForm()

    if request.method == "GET" and current_user.is_authenticated:
        form.name.data = f"{current_user.first_name} {current_user.last_name}"
        form.email.data = current_user.email

    if form.validate_on_submit():
        new_message = Contact(
            name=form.name.data,
            email=form.email.data,
            body=form.message.data
        )
        db.session.add(new_message)
        db.session.commit()

        flash("Your message has been successfully received.", "success")
        return redirect(url_for("contact"))

    return render_template("contact.html", form=form)



if __name__ == "__main__":
    app.run(port=5001, debug=True)
