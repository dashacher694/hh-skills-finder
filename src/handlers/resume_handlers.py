import os
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext

from src.core.states import SkillSearchStates
from src.services.resume_parser import ResumeParser
from src.services.hh_client import HeadHunterClient
from src.core.resume_models import ResumeAnalysis, Resume

router = Router()
resume_parser = ResumeParser()
hh_client = HeadHunterClient()


@router.message(Command("upload_resume"))
async def handle_upload_resume(message: Message, state: FSMContext):
    await message.answer(
        "Загрузите ваше резюме в формате PDF или Word.\n\n"
        "Я проанализирую его и сравню с требованиями рынка."
    )
    await state.set_state(SkillSearchStates.waiting_for_resume)


@router.message(SkillSearchStates.waiting_for_resume, F.document)
async def process_resume_file(message: Message, state: FSMContext):
    document = message.document
    
    if not document.file_name.lower().endswith(('.pdf', '.docx', '.doc')):
        await message.answer(
            "Поддерживаются только файлы PDF и Word (.docx, .doc).\n"
            "Пожалуйста, загрузите файл в правильном формате."
        )
        return
    
    processing_msg = await message.answer("Обрабатываю резюме...")
    
    try:
        file = await message.bot.get_file(document.file_id)
        file_path = f"/tmp/{document.file_name}"
        await message.bot.download_file(file.file_path, file_path)
        
        resume = await resume_parser.parse_file(file_path)
        
        await state.update_data(resume=resume.to_dict())
        
        await processing_msg.delete()
        await message.answer(resume.format_summary())
        
        await message.answer(
            "Хотите сравнить ваше резюме с требованиями рынка?\n"
            "Введите название профессии для анализа:"
        )
        await state.set_state(SkillSearchStates.waiting_for_profession_for_comparison)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            
    except Exception as e:
        await processing_msg.delete()
        await message.answer(
            f"Произошла ошибка при обработке файла: {str(e)}\n"
            "Попробуйте загрузить файл снова."
        )
        await state.clear()


@router.message(SkillSearchStates.waiting_for_profession_for_comparison, F.text)
async def compare_with_market(message: Message, state: FSMContext):
    profession = message.text.strip()
    user_data = await state.get_data()
    resume_data = user_data.get("resume")
    
    if not resume_data:
        await message.answer("Резюме не найдено. Загрузите резюме снова с помощью /upload_resume")
        await state.clear()
        return

    resume = Resume.from_dict(resume_data)
    
    processing_msg = await message.answer(
        f"Анализирую рынок для профессии '{profession}'...\n"
        "Это может занять некоторое время."
    )
    
    try:
        market_analysis = await hh_client.analyze_skills(profession, 30)
        
        market_skills = [skill.name.lower() for skill in market_analysis.top_skills]
        resume_skills = [skill.lower() for skill in resume.skills]
        
        matching_skills = [skill for skill in resume_skills if skill.lower() in market_skills]
        missing_skills = [skill for skill in market_skills if skill.lower() not in resume_skills]
        
        competitiveness_score = (len(matching_skills) / len(market_skills) * 10) if market_skills else 0
        
        recommendations = []
        if missing_skills:
            top_missing = missing_skills[:5]
            recommendations.append(
                f"Добавьте в резюме следующие востребованные навыки: {', '.join(top_missing)}"
            )
        
        if competitiveness_score < 5:
            recommendations.append(
                "Ваше резюме значительно отстает от требований рынка. "
                "Рекомендуем пройти курсы по недостающим технологиям."
            )
        elif competitiveness_score < 7:
            recommendations.append(
                "Резюме соответствует базовым требованиям, но есть куда расти."
            )
        else:
            recommendations.append(
                "Отличное резюме! Вы соответствуете большинству требований рынка."
            )
        
        if not resume.position or len(resume.position) < 10:
            recommendations.append(
                f"Оптимизируйте заголовок резюме. Используйте формат: '{profession} | {', '.join(matching_skills[:3])}'"
            )
        
        analysis = ResumeAnalysis(
            resume=resume,
            market_skills=market_skills,
            missing_skills=missing_skills,
            matching_skills=matching_skills,
            competitiveness_score=competitiveness_score,
            recommendations=recommendations
        )
        
        await processing_msg.delete()
        await message.answer(analysis.format_report())
        
        if market_analysis.salary_stats and market_analysis.salary_stats.avg_salary:
            salary_msg = f"\n💰 Средняя зарплата на рынке: {market_analysis.salary_stats.format_salary(market_analysis.salary_stats.avg_salary)}"
            await message.answer(salary_msg)
        
    except Exception as e:
        await processing_msg.delete()
        await message.answer(
            f"Произошла ошибка при анализе: {str(e)}\n"
            "Попробуйте позже."
        )
    finally:
        await state.clear()


@router.message(SkillSearchStates.waiting_for_resume)
async def invalid_resume_file(message: Message):
    await message.answer(
        "Пожалуйста, загрузите файл резюме в формате PDF или Word.\n"
        "Используйте кнопку прикрепления файла."
    )
