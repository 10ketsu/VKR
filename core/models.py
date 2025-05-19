from sqlalchemy import Column, Integer, BIGINT, DateTime, String, Boolean, JSON, func, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(BIGINT, primary_key=True, index=True)
    username = Column(String(256))
    full_name = Column(String(256))
    created_at = Column(DateTime, default=func.now())

    recommendations = relationship('Recommendation', back_populates='user')


class Game(Base):
    __tablename__ = 'games'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(256))
    short_description = Column(String())
    description = Column(String())
    developers = Column(JSON, default=[])
    genres = Column(JSON, default=[])
    categories = Column(JSON, default=[])
    platforms = Column(JSON, default={})
    recommendations = Column(Integer, default=0)
    supported_languages = Column(String())
    is_free = Column(Boolean())
    normalized = Column(String())


class Recommendation(Base):
    __tablename__ = 'recommendation_history'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BIGINT, ForeignKey('users.id'), nullable=False)
    genres = Column(JSON, default=[])
    categories = Column(JSON, default=[])
    created_at = Column(DateTime, default=func.now())

    user = relationship('User', back_populates='recommendations')


class MuteGame(Base):
    __tablename__ = 'mute_games'

    user_id = Column(BIGINT, ForeignKey('users.id'), primary_key=True, nullable=False)
    game_id = Column(Integer, ForeignKey('games.id'), primary_key=True, nullable=False)