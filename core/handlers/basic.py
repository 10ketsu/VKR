from aiogram import F, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models
from core.config import dp


@dp.callback_query(F.data == 'start')
async def start(data, state: FSMContext, session: AsyncSession):
    message: types.Message = data.message if isinstance(data, types.CallbackQuery) else data
    await state.clear()

    if not await session.scalar(select(models.User).where(models.User.id == message.chat.id)):
        session.add(models.User(id=message.chat.id, username=message.chat.username, full_name=message.chat.full_name))
        await session.commit()

    keyboard = InlineKeyboardBuilder()
    keyboard.add(types.InlineKeyboardButton(text='🎲 Случайная игра', callback_data='random_game'))
    keyboard.add(types.InlineKeyboardButton(text='🏷 Поиск по тегам', callback_data='tags_search'))
    keyboard.add(types.InlineKeyboardButton(text='💬 Рекомендации', callback_data='recommendations'))
    keyboard.adjust(1)

    text = 'Главное меню'
    try:
        await message.edit_text(text, reply_markup=keyboard.as_markup())
    except:
        if isinstance(data, types.CallbackQuery):
            await data.answer()
        await message.answer(text, reply_markup=keyboard.as_markup())


@dp.callback_query(F.data.startswith('mute_game_'))
async def mute_game(call: types.CallbackQuery, session: AsyncSession):
    game_id = int(call.data.split('_')[-1])
    mutes = (await session.execute(select(models.MuteGame.game_id).where(models.MuteGame.user_id == call.message.chat.id))).scalars().all()
    if game_id in mutes:
        return await call.answer('Уже выполнено')
    session.add(models.MuteGame(user_id=call.message.chat.id, game_id=game_id))
    await session.commit()
    await call.answer('✅ Игра больше не будет показываться')