"""Database layer for the bilingual Telegram movie catalog bot."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, create_engine, select, or_, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def make_database_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite:///./moviebot.db").strip()
    # Render and some other hosts still provide the older postgres:// format.
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://") and "+psycopg" not in url:
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


DATABASE_URL = make_database_url()
engine_options = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    language: Mapped[str] = mapped_column(String(2), default="uz", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)


class Film(Base):
    __tablename__ = "films"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title_uz: Mapped[str] = mapped_column(String(200), nullable=False)
    title_ru: Mapped[str] = mapped_column(String(200), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    genre_uz: Mapped[str] = mapped_column(String(100), nullable=False)
    genre_ru: Mapped[str] = mapped_column(String(100), nullable=False)
    rating: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    description_uz: Mapped[str] = mapped_column(Text, nullable=False)
    description_ru: Mapped[str] = mapped_column(Text, nullable=False)
    poster_file_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    watch_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    video_file_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)


class Favorite(Base):
    __tablename__ = "favorites"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), primary_key=True)
    film_id: Mapped[int] = mapped_column(Integer, ForeignKey("films.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)


class Watched(Base):
    __tablename__ = "watched"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), primary_key=True)
    film_id: Mapped[int] = mapped_column(Integer, ForeignKey("films.id", ondelete="CASCADE"), primary_key=True)
    watched_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)


def init_db() -> None:
    Base.metadata.create_all(engine)


def upsert_user(telegram_id: int, username: Optional[str]) -> None:
    with SessionLocal() as session:
        user = session.get(User, telegram_id)
        if user is None:
            session.add(User(telegram_id=telegram_id, username=username, language="uz"))
        else:
            user.username = username
        session.commit()


def get_language(telegram_id: int) -> str:
    with SessionLocal() as session:
        user = session.get(User, telegram_id)
        return user.language if user and user.language in {"uz", "ru"} else "uz"


def set_language(telegram_id: int, language: str) -> None:
    if language not in {"uz", "ru"}:
        return
    with SessionLocal() as session:
        user = session.get(User, telegram_id)
        if user is None:
            user = User(telegram_id=telegram_id, language=language)
            session.add(user)
        else:
            user.language = language
        session.commit()


def add_film(data: dict) -> int:
    with SessionLocal() as session:
        film = Film(**data)
        session.add(film)
        session.commit()
        session.refresh(film)
        return film.id


def get_film(film_id: int) -> Optional[Film]:
    with SessionLocal() as session:
        return session.get(Film, film_id)


def delete_film(film_id: int) -> bool:
    with SessionLocal() as session:
        film = session.get(Film, film_id)
        if film is None:
            return False
        session.delete(film)
        session.query(Favorite).filter(Favorite.film_id == film_id).delete(synchronize_session=False)
        session.query(Watched).filter(Watched.film_id == film_id).delete(synchronize_session=False)
        session.commit()
        return True


def search_films(query: str, user_id: int, mode: str = "all") -> list[Film]:
    """Return all matching films; pagination is handled by the UI layer."""
    with SessionLocal() as session:
        stmt = select(Film)
        if mode == "favorites":
            stmt = stmt.join(Favorite, Favorite.film_id == Film.id).where(Favorite.user_id == user_id)
        elif mode == "watched":
            stmt = stmt.join(Watched, Watched.film_id == Film.id).where(Watched.user_id == user_id).order_by(Watched.watched_at.desc())
        elif mode.startswith("genre:"):
            key = mode.split(":", 1)[1]
            pairs = session.execute(select(Film.genre_uz, Film.genre_ru).distinct()).all()
            pair = next(((uz, ru) for uz, ru in pairs if genre_key(uz, ru) == key), None)
            if pair is None:
                return []
            stmt = stmt.where(Film.genre_uz == pair[0], Film.genre_ru == pair[1])
        if query.strip():
            pattern = f"%{query.strip()}%"
            stmt = stmt.where(or_(Film.title_uz.ilike(pattern), Film.title_ru.ilike(pattern),
                                  Film.description_uz.ilike(pattern), Film.description_ru.ilike(pattern),
                                  Film.genre_uz.ilike(pattern), Film.genre_ru.ilike(pattern)))
        if mode != "watched":
            stmt = stmt.order_by(Film.created_at.desc(), Film.id.desc())
        return list(session.scalars(stmt).all())


def list_genres() -> list[tuple[str, str]]:
    with SessionLocal() as session:
        rows = session.execute(select(Film.genre_uz, Film.genre_ru).distinct().order_by(Film.genre_uz)).all()
        return [(row[0], row[1]) for row in rows]


def genre_key(genre_uz: str, genre_ru: str) -> str:
    # Stable short key, safe to place in Telegram callback_data.
    import hashlib
    return hashlib.sha1(f"{genre_uz}|{genre_ru}".encode("utf-8")).hexdigest()[:12]


def is_favorite(user_id: int, film_id: int) -> bool:
    with SessionLocal() as session:
        return session.get(Favorite, (user_id, film_id)) is not None


def toggle_favorite(user_id: int, film_id: int) -> bool:
    with SessionLocal() as session:
        key = (user_id, film_id)
        entry = session.get(Favorite, key)
        if entry:
            session.delete(entry)
            session.commit()
            return False
        session.add(Favorite(user_id=user_id, film_id=film_id))
        session.commit()
        return True


def is_watched(user_id: int, film_id: int) -> bool:
    with SessionLocal() as session:
        return session.get(Watched, (user_id, film_id)) is not None


def toggle_watched(user_id: int, film_id: int) -> bool:
    with SessionLocal() as session:
        key = (user_id, film_id)
        entry = session.get(Watched, key)
        if entry:
            session.delete(entry)
            session.commit()
            return False
        session.add(Watched(user_id=user_id, film_id=film_id))
        session.commit()
        return True


def get_stats() -> dict[str, int]:
    with SessionLocal() as session:
        return {
            "films": session.scalar(select(func.count()).select_from(Film)) or 0,
            "users": session.scalar(select(func.count()).select_from(User)) or 0,
            "favorites": session.scalar(select(func.count()).select_from(Favorite)) or 0,
            "watched": session.scalar(select(func.count()).select_from(Watched)) or 0,
        }
