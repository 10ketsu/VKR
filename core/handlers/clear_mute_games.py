from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from core import models
from core.config import dp
from aiogram.fsm.state import StatesGroup, State


class ClearMuteStates(StatesGroup):
    waiting_for_names = State()


@dp.message(Command("clear_mute_games"))
async def clear_mute_games(message: types.Message, session: AsyncSession, state: FSMContext):
    mutes = (await session.execute(
        select(models.MuteGame.game_id).where(models.MuteGame.user_id == message.chat.id)
    )).scalars().all()

    if not mutes:
        return await message.answer("У вас нет исключенных для рекомендаций игр.")

    games = (await session.execute(
        select(models.Game).where(models.Game.id.in_(mutes))
    )).scalars().all()

    text = "Список исключенных из рекомендаций игр:\n\n"
    text += "\n".join(f"• {game.name}" for game in games)

    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        types.InlineKeyboardButton(text="Очистить все", callback_data="clear_all_mutes"),
        types.InlineKeyboardButton(text="В меню", callback_data="start")
    )

    await message.answer(
        text + "\n\nВведите названия игр, которые нужно удалить (по одному или через запятую):",
        reply_markup=keyboard.as_markup()
    )
    await state.set_state(ClearMuteStates.waiting_for_names)


@dp.callback_query(F.data == "clear_all_mutes")
async def clear_all_mutes(call: types.CallbackQuery, session: AsyncSession, state: FSMContext):
    await session.execute(
        delete(models.MuteGame).where(models.MuteGame.user_id == call.message.chat.id)
    )
    await session.commit()
    await state.clear()
    await call.answer("теперь нет исключаемых игр")
    await call.message.edit_text("Список очищен.")


@dp.message(ClearMuteStates.waiting_for_names)
async def delete_selected_mutes(message: types.Message, session: AsyncSession, state: FSMContext):
    names = [name.strip().lower() for name in message.text.split(",")]

    mutes = (await session.execute(
        select(models.MuteGame.game_id).where(models.MuteGame.user_id == message.chat.id)
    )).scalars().all()

    if not mutes:
        return await message.answer("У вас нет исключенных для рекомендаций игр.")

    games = (await session.execute(
        select(models.Game).where(models.Game.id.in_(mutes))
    )).scalars().all()

    matched = [game for game in games if game.name.wlower() in names]

    if not matched:
        return await message.answer("Не удалось найти совпадений по названиям.")

    for game in matched:
        await session.execute(
            delete(models.MuteGame).where(
                models.MuteGame.user_id == message.chat.id,
                models.MuteGame.game_id == game.id
            )
        )

    await session.commit()
    await state.clear()
    await message.answer(f"Удалено {len(matched)} игр из списка исключений.")
