from typing import List
from datetime import date
from flask import Flask, render_template, redirect, url_for, request
# from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer, String, Text, ForeignKey, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from forms import CreatePostForm

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
# Bootstrap5(app)

#Initalize DB
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///travel-blog-posts.db"
db.init_app(app)



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
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)


with app.app_context():
    db.create_all()


@app.route('/')
def get_all_posts():
    all_posts = db.session.execute(db.select(BlogPost)).scalars().all()

    return render_template('index.html', posts=all_posts)

@app.route('/add', methods=['GET', 'POST'])
def create_post():
    form = CreatePostForm()
    add_post_page = True

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
            img_url=form.img_url.data
        )
        db.session.add(new_post)
        db.session.commit()
        add_post_page = False

        return redirect(url_for('get_all_posts', is_add_page=add_post_page))

    return render_template('add-post.html', form=form, is_add_page=add_post_page)


if __name__ == '__main__':
    app.run(port=5001, debug=True)
