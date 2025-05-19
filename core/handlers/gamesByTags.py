from aiogram import F, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models
from core.config import dp
from core.utils import find_games_by_tags, send_games
from core.variables import tags_questions


@dp.callback_query(F.data.in_(['tags_search', 'prev_tags', 'next_tags']))
async def tags_search(call: types.CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    if call.data in ['prev_tags', 'next_tags']:
        if call.data == 'next_tags' and state_data.get('index', 0) == len(tags_questions) - 1:
            return await tags_games_list(call, state)

        state_data['index'] = state_data.get('index', 0) + (1 if call.data == 'next_tags' else -1)
        await state.update_data(index=state_data['index'])
    quest = tags_questions[state_data.get('index', 0)]
    sel = state_data.get('tags', [[] for _ in range(len(tags_questions))])[state_data.get('index', 0)]

    keyboard = InlineKeyboardBuilder()
    for i, way in enumerate(quest['variants']):
        text = '✅ ' + way['text'] if i in sel else '⬜️ ' + way['text']
        keyboard.add(types.InlineKeyboardButton(text=text, callback_data='tag_' + str(i)))
    keyboard.adjust(2)

    if state_data.get('index', 0) > 0:
        keyboard.row(types.InlineKeyboardButton(text='⬅️ Назад', callback_data='prev_tags'),
                     types.InlineKeyboardButton(text='➡️ Далее' if sel else '➡️ Пропустить', callback_data='next_tags'))
    else:
        keyboard.row(types.InlineKeyboardButton(text='➡️ Далее' if sel else '➡️ Пропустить', callback_data='next_tags'))
    keyboard.row(types.InlineKeyboardButton(text='🔎 Начать поиск', callback_data='start_search'))
    keyboard.row(types.InlineKeyboardButton(text='В меню', callback_data='start'))

    page = f'\n\nстр. {state_data.get("index", 0) + 1}/{len(tags_questions)}'
    try:
        await call.message.edit_text(quest['question'] + page, reply_markup=keyboard.as_markup())
    except:
        await call.answer()
        await call.message.answer(quest['question'] + page, reply_markup=keyboard.as_markup())


@dp.callback_query(F.data.startswith('tag_'))
async def tags_select(call: types.CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    tags = state_data.get('tags', [[] for _ in range(len(tags_questions))])
    i, index = int(call.data.split('_')[1]), state_data.get('index', 0)

    tags[index].remove(i) if i in tags[index] else tags[index].append(i)
    await state.update_data(tags=tags)
    await tags_search(call, state)


@dp.callback_query(F.data.in_(['prev_tags_game', 'next_tags_game', 'start_search']))
async def tags_games_list(call: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    state_data = await state.get_data()
    if not state_data.get('games') or 'start_search':
        tags = state_data.get('tags', [[] for _ in range(len(tags_questions))])
        mutes_exec = await session.execute(select(models.MuteGame.game_id).where(models.MuteGame.user_id == call.message.chat.id))
        mutes = mutes_exec.scalars().all()
        state_data['games'] = [g for g in await find_games_by_tags(tags) if g not in mutes]
        await state.update_data(games=state_data['games'])

    delta = 1 if call.data == 'next_tags_game' else -1 if call.data == 'prev_tags_game' else 0
    i_game = state_data.get('i_game', 0) + delta
    game = await session.scalar(select(models.Game).where(models.Game.id == state_data['games'][i_game]))
    await state.update_data(i_game=i_game)

    keyboard = InlineKeyboardBuilder()
    keyboard.add(types.InlineKeyboardButton(text='➖ Не показывать', callback_data=f'mute_game_{game.id}'))
    keyboard.add(types.InlineKeyboardButton(text='ℹ️ Подробнее', url=f'https://store.steampowered.com/app/{game.id}'))
    keyboard.add(types.InlineKeyboardButton(text='⬅️ Назад', callback_data='prev_tags_game' if i_game else 'tags_search'))
    if i_game < len(state_data['games']) - 1:
        keyboard.add(types.InlineKeyboardButton(text='➡️ Далее', callback_data='next_tags_game'))
    keyboard.row(types.InlineKeyboardButton(text='В меню', callback_data='start'))
    keyboard.adjust(2, 2, 1)

    await call.answer()
    await send_games(call.message, game, keyboard)