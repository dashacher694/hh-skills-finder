from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from src.core.states import SkillSearchStates
from src.services.hh_client import HeadHunterClient

router = Router()
hh_client = HeadHunterClient()


@router.message(CommandStart())
async def handle_start(message: Message):
    welcome_text = (
        "Привет! Я помогу найти востребованные навыки и улучшить резюме.\n\n"
        "Доступные команды:\n"
        "/find - Анализ рынка по профессии\n"
        "/upload_resume - Загрузить и проанализировать резюме"
    )
    await message.answer(welcome_text)


@router.message(Command("find"))
async def handle_find_command(message: Message, state: FSMContext):
    await message.answer(
        "Введите название профессии или специальности для анализа:"
    )
    await state.set_state(SkillSearchStates.waiting_for_profession)


@router.message(SkillSearchStates.waiting_for_profession, F.text)
async def process_profession(message: Message, state: FSMContext):
    profession = message.text.strip()
    
    await state.update_data(profession=profession)
    await message.answer(
        f"Профессия: {profession}\n\n"
        "Укажите количество вакансий для анализа (от 1 до 100):"
    )
    await state.set_state(SkillSearchStates.waiting_for_vacancy_count)


@router.message(SkillSearchStates.waiting_for_vacancy_count, F.text.regexp(r"^\d+$"))
async def process_vacancy_count(message: Message, state: FSMContext):
    count = int(message.text)
    
    if count < 1 or count > 100:
        await message.answer("Укажите число от 1 до 100")
        return
    
    user_data = await state.get_data()
    profession = user_data.get("profession", "")
    
    processing_msg = await message.answer(
        f"Анализирую {count} вакансий по запросу '{profession}'...\n"
        "Это может занять некоторое время."
    )
    
    try:
        result = await hh_client.analyze_skills(profession, count)
        await processing_msg.delete()
        await message.answer(result.format_message())
    except Exception as e:
        await processing_msg.delete()
        await message.answer(
            "Произошла ошибка при анализе. Попробуйте позже или измените запрос."
        )
    finally:
        await state.clear()


@router.message(SkillSearchStates.waiting_for_vacancy_count)
async def invalid_count_format(message: Message):
    await message.answer("Пожалуйста, введите число от 1 до 100")
