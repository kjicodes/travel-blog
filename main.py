import os
from datetime import date
from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer, String, Text, ForeignKey, Boolean, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from werkzeug.security import generate_password_hash, check_password_hash
from forms import CreatePostForm, LoginForm, RegisterForm, ContactForm, CommentForm
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
app.config["WTF_CSRF_TIME_LIMIT"] = None
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

    posts = relationship("BlogPost", back_populates="user")
    comments = relationship("Comment", back_populates="user")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    location: Mapped[str] = mapped_column(String(250), nullable=False)
    num_times_visited: Mapped[int] = mapped_column(Integer, nullable=False)
    visit_again: Mapped[bool] = mapped_column(Boolean, nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    rating: Mapped[str] = mapped_column(String(250), nullable=False)
    img_url: Mapped[str] = mapped_column(Text, nullable=False)

    user_id = mapped_column(ForeignKey("users.id"))
    user = relationship("User", back_populates="posts")

    comments = relationship("Comment", back_populates="post")

    def calc_comments_count(self):
        return len(self.comments)

class Comment(db.Model):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(primary_key=True)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)

    user_id = mapped_column(ForeignKey("users.id"))
    user = relationship("User", back_populates="comments")

    post_id = mapped_column(ForeignKey("blog_posts.id"))
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


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method="pbkdf2", salt_length=8)

        try:
            new_user = User(
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                email=form.email.data,
                password=hashed_password
            )
            db.session.add(new_user)
            db.session.commit()
        except IntegrityError:
            flash("Email already exists. Please login in.", "error")
            return redirect(url_for("login"))
        else:
            flash("Account successfully registered. Please log in.", "success")
            return redirect(url_for("login"))

    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.execute(db.select(User).where(User.email == form.email.data)).scalar()
        if user:
            stored_password = user.password
            if check_password_hash(stored_password, form.password.data):
                login_user(user)
                return redirect(url_for("get_all_posts"))
            else:
                flash("Invalid password. Please try again.", "error")
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

@app.route("/post/<post_id>", methods=["GET", "POST"])
def get_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    comments = db.session.execute(db.select(Comment).where(Comment.post == post).order_by(desc(Comment.id))).scalars().all()

    total_comments = len(comments)

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

            return redirect(url_for('get_post', post_id=post.id))
        else:
            flash('Please log in.', 'error')
            return redirect(url_for('login'))

    return render_template("post.html", post=post, form=form, comments=comments, total_comments=total_comments)

@app.route('/add-post', methods=["GET", "POST"])
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

        return redirect(url_for('get_post', post_id=post_id))

    return render_template('add-post.html', form=form)

@app.route('/edit-post/<post_id>', methods=['GET', 'POST'])
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
        return redirect(url_for('get_post', post_id=post.id))

    return render_template('add-post.html', form=edit_form, is_edit=True)

@app.route('/delete-post/<post_id>')
@login_required
def delete_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    db.session.delete(post)
    db.session.commit()

    return redirect(url_for('get_all_posts'))

@app.route("/delete-comment/<comment_id>")
@login_required
def delete_comment(comment_id):
    comment = db.get_or_404(Comment, comment_id)
    db.session.delete(comment)
    db.session.commit()



    return redirect(url_for('get_post', post_id=comment.post_id))


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()

    if form.validate_on_submit():
        new_message = Contact(
            name=form.name.data,
            email=form.email.data,
            body=form.message.data
        )
        db.session.add(new_message)
        db.session.commit()

        flash('Your message has been successfully received.', 'success')

        return redirect(url_for('contact'))


    return render_template('contact.html', form=form)



if __name__ == '__main__':
    app.run(port=5001, debug=True)
