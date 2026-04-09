from flask_login import UserMixin
from sqlalchemy import ForeignKey, String, Integer, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(250), nullable=False)
    last_name: Mapped[str] = mapped_column(String(250), nullable=False)
    email: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(250), nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False)
    verification_token: Mapped[str] = mapped_column(String(250), nullable=True)
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