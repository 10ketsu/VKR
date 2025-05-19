import asyncio
import os
import time
import dotenv
import requests
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from core import models
from core.models import Base
from core.utils import game_to_normalize


async def load(session: AsyncSession):
    top = set()
    for i in range(4, -1, -1):
        req = f'all&page={i}' if i < 3 else 'top100owned' if i == 3 else 'top100forever'
        res = requests.get(f'https://steamspy.com/api.php?request={req}')
        for _, game in res.json().items():
            if (game['positive'] > 50000
                    or (game['negative'] and game['positive'] > 30000 and game['positive'] / game['negative'] > 2)
                    or (game['negative'] and game['positive'] > 10000 and game['positive'] / game['negative'] > 3)):
                top.add(game['appid'])

    top, k = list(top), 0
    for app_id in top:
        try:
            if await session.scalar(select(models.Game).where(models.Game.id == app_id)):
                print(end='.')
                continue
            res = requests.get(f"https://store.steampowered.com/api/appdetails?l=russian&appids={app_id}")
            info = res.json().get(str(app_id), {}).get('data', {})
            if not info or info.get('type') != 'game':
                continue
            game = models.Game(id=int(app_id),
                               name=info.get('name'),
                               short_description=info.get('short_description', ''),
                               description=info.get('detailed_description', ''),
                               developers=info.get('developers', []),
                               genres=info.get('genres', []),
                               categories=info.get('categories', []),
                               platforms=info.get('platforms', {}),
                               recommendations=info.get('recommendations', {}).get('total', 0),
                               supported_languages=info.get('supported_languages', ''),
                               is_free=info.get('is_free'))
            game.normalized = game_to_normalize(game)
            session.add(game)
            await session.commit()
            print(f'{k})', game.name)
            k += 1
            time.sleep(2)
        except Exception as e:
            print(f'Game {app_id} error: ' + str(e))


async def main():
    dotenv.load_dotenv()
    engine = create_async_engine(os.environ.get('DATABASE_URL'))
    async_session_maker = sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        await load(session)


if __name__ == '__main__':
    asyncio.run(main())