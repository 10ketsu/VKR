import random

from aiogram import F, types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models
from core.config import dp
from core.utils import send_games


@dp.callback_query(F.data == 'random_game')
async def random_game(call: types.CallbackQuery, session: AsyncSession):
    mutes = (await session.execute(select(models.MuteGame.game_id).where(models.MuteGame.user_id == call.message.chat.id))).scalars().all()
    games = await session.execute(select(models.Game).where(models.Game.id.notin_(mutes)))
    game = random.choice(games.scalars().all())

    keyboard = InlineKeyboardBuilder()
    keyboard.add(types.InlineKeyboardButton(text='➖ Не показывать', callback_data=f'mute_game_{game.id}'))
    keyboard.add(types.InlineKeyboardButton(text='ℹ️ Подробнее', url=f'https://store.steampowered.com/app/{game.id}'))
    keyboard.add(types.InlineKeyboardButton(text='➡️ Далее', callback_data='random_game'))
    keyboard.add(types.InlineKeyboardButton(text='В меню', callback_data='start'))
    keyboard.adjust(2, 1, 1)

    await call.answer()
    await send_games(call.message, game, keyboard)