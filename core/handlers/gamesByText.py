import logging

from aiogram import F, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models
from core.config import dp, groq_client
from core.utils import find_games, send_games
from aiogram.fsm.state import StatesGroup, State

from core.variables import recommendations_search_prompt


class States(StatesGroup):
    get_search_query = State()


@dp.callback_query(F.data == 'recommendations')
async def recommendations(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(States.get_search_query)

    keyboard = InlineKeyboardBuilder()
    keyboard.add(types.InlineKeyboardButton(text='⬅️ Назад', callback_data='start'))

    await call.message.edit_text('✏️ Введите запрос для поиска игр', reply_markup=keyboard.as_markup())


@dp.message(F.text[0] != '/', States.get_search_query)
async def recommendations_search(message: types.Message, state: FSMContext, session: AsyncSession):
    await message.answer('🔎 Идет поиск игр...')
    res = await groq_client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=[
            {"role": "system", "content": recommendations_search_prompt},
            {"role": "user", "content": message.text}
        ],
    )
    logging.warning(message.text + ' -> ' + res.choices[0].message.content)
    games = await find_games(res.choices[0].message.content, top_n=30)

    user = await session.scalar(select(models.User).where(models.User.id == message.chat.id))
    await session.refresh(user, attribute_names=["recommendations"])
    genres = [gen for r in user.recommendations for gen in r.genres]
    categories = [cat for r in user.recommendations for cat in r.categories]

    for game in games:
        game.rating = 0
        for genre in game.genres:
            game.rating += genres.count(genre['id'])
        for category in game.categories:
            game.rating += categories.count(category['id'])
    games.sort(key=lambda g: g.rating, reverse=True)
    session.add(models.Recommendation(user_id=message.chat.id,
                                      genres=[g['id'] for g in games[0].genres],
                                      categories=[c['id'] for c in games[0].categories]))
    await session.commit()

    mutes_exec = await session.execute(select(models.MuteGame.game_id).where(models.MuteGame.user_id == message.chat.id))
    mutes = mutes_exec.scalars().all()
    await state.update_data(games=[game.id for game in games if game.id not in mutes])
    await games_list(message, state, session)


@dp.callback_query(F.data.in_(['prev_game', 'next_game']))
async def games_list(data, state: FSMContext, session: AsyncSession):
    message = data.message if isinstance(data, types.CallbackQuery) else data
    state_data = await state.get_data()

    delta = 0
    if isinstance(data, types.CallbackQuery):
        await data.answer()
        delta = 1 if data.data == 'next_game' else -1 if data.data == 'prev_game' else 0
    i_game = state_data.get('i_game', 0) + delta
    game = await session.scalar(select(models.Game).where(models.Game.id == state_data['games'][i_game]))
    await state.update_data(i_game=i_game)

    keyboard = InlineKeyboardBuilder()
    keyboard.add(types.InlineKeyboardButton(text='➖ Не показывать', callback_data=f'mute_game_{game.id}'))
    keyboard.add(types.InlineKeyboardButton(text='ℹ️ Подробнее', url=f'https://store.steampowered.com/app/{game.id}'))
    keyboard.add(types.InlineKeyboardButton(text='⬅️ Назад', callback_data='prev_game' if i_game else 'recommendations'))
    if i_game < len(state_data['games']) - 1:
        keyboard.add(types.InlineKeyboardButton(text='➡️ Далее', callback_data='next_game'))
    keyboard.row(types.InlineKeyboardButton(text='В меню', callback_data='start'))
    keyboard.adjust(2, 2, 1)

    await send_games(message, game, keyboard)