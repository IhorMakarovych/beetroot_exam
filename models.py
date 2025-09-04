from sqlmodel import SQLModel, Field, Relationship, Session, create_engine
from typing import List, Optional
from datetime import datetime
from passlib.hash import bcrypt
import os

DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///./recipes.db')
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False})


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str
    session_token: Optional[str] = None
    created_at: datetime = datetime.utcnow()

    def verify_password(self, password: str) -> bool:
        return bcrypt.verify(password, self.password_hash)


class Recipe(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    type: str
    min_time: Optional[int] = 0
    max_time: Optional[int] = 0
    image: Optional[str] = None
    author_id: Optional[int] = Field(default=None, foreign_key='user.id')

    ingredients: List["Ingredient"] = Relationship(
        back_populates='recipe',
        sa_relationship_kwargs={'cascade': 'all, delete-orphan', 'lazy': 'selectin'}
    )
    steps: List["Step"] = Relationship(
        back_populates='recipe',
        sa_relationship_kwargs={'cascade': 'all, delete-orphan', 'lazy': 'selectin'}
    )


class Ingredient(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    recipe_id: int = Field(foreign_key='recipe.id', nullable=False)
    name: str
    qty: str

    recipe: Optional[Recipe] = Relationship(
        back_populates='ingredients',
        sa_relationship_kwargs={'lazy': 'selectin'}
    )


class Step(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    recipe_id: int = Field(foreign_key='recipe.id', nullable=False)
    order: int
    description: str

    recipe: Optional[Recipe] = Relationship(
        back_populates='steps',
        sa_relationship_kwargs={'lazy': 'selectin'}
    )


def init_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session

