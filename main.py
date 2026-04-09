import os
from datetime import date
from flask_mail import Mail, Message
from smtplib import SMTPException
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_bootstrap import Bootstrap5
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from forms import CreatePostForm, LoginForm, RegisterForm, ContactForm, CommentForm
from flask_wtf.csrf import CSRFError
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
from extensions import db
from models import User, BlogPost, Comment, Contact

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
#Configure mail service
app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER")
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USE_SSL"] = False
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_USERNAME")

Bootstrap5(app)

#Configure db
uri = os.environ.get("DATABASE_URL", "sqlite:///travel-blog-posts.db")
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = uri
db.init_app(app)
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


def generate_verification_token(user_id):
    auth_s = URLSafeTimedSerializer(app.config["SECRET_KEY"])
    token = auth_s.dumps(user_id, salt="verify-email")
    return token

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
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

        try:
            db.session.commit()
        except IntegrityError as e:
            app.logger.error(f"Email already exists: {e}")
            flash("Email already exists. Please login in.", "error")
            return redirect(url_for("login"))
        else:
            #Build confirmation URL and include in the verification email
            token = generate_verification_token(new_user.id)
            new_user.verification_token = token
            db.session.commit()
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
            except SMTPException as e:
                app.logger.error(f"Failed to send confirmation email: {e}")
                flash("Failed to send confirmation email. Please try again.", "error")
                return render_template("verify-email.html", user=new_user)
            else:
                return render_template("verify-email.html", user=new_user)

    return render_template("register.html", form=form)

@app.route("/register/verify/<int:user_id>")
def resend_verification_email(user_id):
    user = db.session.get(User, user_id)
    token = generate_verification_token(user.id)
    user.verification_token = token
    db.session.commit()
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
    except SMTPException as e:
        app.logger.error(f"Failed to send confirmation email: {e}")
        flash("Failed to send confirmation email. Please try again.", "error")
        return render_template("verify-email.html", user=user)
    else:
        flash("Confirmation email resent.", "info")
        return render_template("verify-email.html", user=user)


@app.route("/verify/<token>")
def verify_email(token):
    auth_s = URLSafeTimedSerializer(app.config["SECRET_KEY"])
    try:
        user_id = auth_s.loads(token, salt="verify-email", max_age=86400)
    except SignatureExpired as e:
        user_id = e.payload
        app.logger.error(f"Verification link has expired: {e}")
        flash("Verification link has expired.", "error")
        return redirect(url_for("login", unverified_user_id=user_id))
    except BadSignature as e:
        app.logger.error(f"Invalid verification link: {e}")
        flash("Invalid verification link.", "error")
        return redirect(url_for("login"))
    else:
        user = db.session.get(User, user_id)
        if user.is_verified:
            flash("Your email has already been verified. Please log in.", "info")
            return redirect(url_for("login"))
        if user.verification_token == token:
            user.is_verified = True
            user.verification_token = None
            db.session.commit()
            flash("Email successfully verified. You can now log in.", "success")
            return redirect(url_for("login"))
        else:
            flash("This verification link is no longer valid. Please use the most recent link sent to your email.", "error")
            return redirect(url_for("login", unverified_user_id=user.id))


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
                    flash("Incorrect password. Please try again.", "error")
            else:
                flash("Please verify your email before logging in.", "error")
                # print(user.id)
                return redirect(url_for("login", unverified_user_id=user.id))
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
