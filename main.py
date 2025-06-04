import asyncio
import logging

import requests
import schedule
from aiogram import types, F
from aiogram.filters import Command
from sqlalchemy import select

from core.config import dp, bot
from core import models
from core.database import async_session_maker, init_db
from core.handlers import basic
from core.handlers.gamesByTags import tags_search
from core.handlers.gamesByText import recommendations
from core.handlers.randomGames import random_game
from core.middleware import Middleware

from core.handlers import clear_mute_games



async def main():
    await init_db()
    dp.update.middleware(Middleware())
    dp.message.register(basic.start, Command('start'))
    dp.callback_query.register(random_game, F.data == 'random_game')
    dp.callback_query.register(tags_search, F.data == 'tags_search')
    dp.callback_query.register(recommendations, F.data == 'recommendations')

    await bot.set_my_commands([
        types.BotCommand(command="start", description="Старт"),
        types.BotCommand(command="clear_mute_games", description="Очистить список исключенных игр"),
    ])
    asyncio.create_task(update_games_scheduler())
    await dp.start_polling(bot)


async def update_games_scheduler():
    schedule.every().day.at('00:00').do(lambda: asyncio.create_task(update_games()))
    while True:
        schedule.run_pending()
        await asyncio.sleep(10)


async def update_games():
    logging.warning('Updating games')
    async with async_session_maker() as session:
        games = await session.scalars(select(models.Game))

    for game in games.all():
        try:
            res = requests.get(f"https://store.steampowered.com/api/appdetails?l=russian&appids={game.id}")
            info = res.json().get(str(game.id), {}).get('data', {})
            updated_game = {'name': info.get('name'),
                            'short_description': info.get('short_description', ''),
                            'description': info.get('detailed_description', ''),
                            'developers': info.get('developers', []),
                            'genres': info.get('genres', []),
                            'categories': info.get('categories', []),
                            'platforms': info.get('platforms', {}),
                            # 'recommendations': info.get('recommendations', {}).get('total', 0),
                            'supported_languages': info.get('supported_languages', ''),
                            'is_free': info.get('is_free')}

            updated = False
            for key in updated_game:
                if updated_game[key] and updated_game[key] != getattr(game, key):
                    setattr(game, key, updated_game[key])
                    updated = True

            if updated:
                session.add(game)
                await session.commit()
            await asyncio.sleep(3)
        except Exception as e:
            print(f'{game.name} update error: ' + str(e))


print('Start working')
if __name__ == "__main__":
    asyncio.run(main())