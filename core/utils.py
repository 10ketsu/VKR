from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select

from core import models
from core.config import morph
from core.database import async_session_maker
from core.variables import tags_questions


def normalize(text: str) -> str:
    return ' '.join(morph.parse(word)[0].normal_form for word in text.split())


def game_to_normalize(game: models.Game) -> str:
    genres = ' '.join([genre['description'] for genre in game.genres])
    categories = ' '.join([category['description'] for category in game.categories])
    return normalize(game.name + '\n' + game.description + '\n' + genres + '\n' + categories)


async def find_games(query: str, top_n=10) -> list:
    async with async_session_maker() as session:
        games: list[models.Game] = (await session.scalars(select(models.Game))).all()

    normalized_games = [game.normalized for game in games]
    normalized_query = normalize(query)

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(normalized_games + [normalized_query])

    cosine_similarities = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1]).flatten()
    top_n_indices = cosine_similarities.argsort()[-top_n:][::-1]

    return [games[i] for i in top_n_indices]


async def find_games_by_tags(tags: list) -> list[int]:
    def num_tags_matches(game: models.Game, user_genres, user_categories):
        num_genres = len([1 for genre in game.genres if int(genre['id']) in user_genres])
        num_categories = len([1 for category in game.categories if int(category['id']) in user_categories])
        return num_genres + num_categories

    tq = tags_questions
    genres = [tq[i]['variants'][j]['id'] for i, t in enumerate(tags) for j in t if tq[i]['params'] == 'genres']
    categories = [tq[i]['variants'][j]['id'] for i, t in enumerate(tags) for j in t if tq[i]['params'] == 'categories']

    async with async_session_maker() as session:
        games: list[models.Game] = (await session.scalars(select(models.Game))).all()

    found = [(num_tags_matches(g, genres, categories), g.recommendations, g.id) for g in games]
    found.sort(reverse=True)
    return [g[2] for g in found[:30] if g[0] > 0]


async def send_games(message: types.Message, game: models.Game, keyboard: InlineKeyboardBuilder) -> None:
    text = (f'<b>{game.name}</b>\n\n'
            f'<i>{game.short_description}</i>\n\n'
            f'Разработчики: {", ".join(["<code>" + dev + "</code>" for dev in game.developers])}\n'
            f'Жанры: {", ".join([genre["description"] for genre in game.genres])}\n')
    url = 'https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/' + str(game.id) + '/header.jpg'
    await message.answer_photo(url, caption=text, reply_markup=keyboard.as_markup())