from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from src.core.states import SkillSearchStates
from src.services.resume_analysis_service import ResumeAnalysisService
from src.core.resume_models import Resume

router = Router()
resume_analysis_service = ResumeAnalysisService()


@router.message(Command("analyze_resume"))
async def handle_analyze_resume(message: Message, state: FSMContext):
    """Запуск углубленного анализа резюме."""
    user_data = await state.get_data()
    resume_data = user_data.get("resume")

    if not resume_data:
        await message.answer(
            "Сначала загрузите резюме с помощью команды /upload_resume"
        )
        return

    resume = Resume.from_dict(resume_data)

    try:
        await message.answer(
            "Укажите целевую должность для анализа (например, 'Python Backend Developer', 'Data Scientist'):"
        )
        await state.set_state(SkillSearchStates.waiting_for_resume_analysis_target)
        await state.update_data(resume_for_analysis=resume.to_dict())

    except Exception as e:
        await message.answer(f"Ошибка запуска анализа: {str(e)}")
        await state.clear()


@router.message(SkillSearchStates.waiting_for_resume_analysis_target, F.text)
async def perform_resume_analysis(message: Message, state: FSMContext):
    """Выполнить углубленный rule-based анализ резюме."""
    target_position = message.text.strip()

    if not target_position:
        await message.answer("Введите целевую должность для углубленного анализа резюме.")
        return

    user_data = await state.get_data()
    resume_data = user_data.get("resume_for_analysis")

    if not resume_data:
        await message.answer("Данные резюме потеряны. Загрузите резюме снова с помощью /upload_resume")
        await state.clear()
        return

    resume = Resume.from_dict(resume_data)

    processing_msg = await message.answer("Анализирую структуру, ключевые слова и качество резюме...")

    try:
        structure_analysis = await resume_analysis_service.analyze_resume_structure(resume)
        skills_analysis = await resume_analysis_service.analyze_skills_relevance(resume, target_position)
        experience_analysis = await resume_analysis_service.analyze_experience_quality(resume)
        ats_analysis = await resume_analysis_service.analyze_ats_filters(resume, target_position)

        await processing_msg.delete()

        analysis_message = format_resume_analysis_report(
            structure_analysis,
            skills_analysis,
            experience_analysis,
            ats_analysis,
            target_position
        )

        await message.answer(analysis_message)

        await message.answer(
            "Вы можете:\n"
            "ввести профессию для сравнения с рынком\n"
            "или загрузить другое резюме через /upload_resume"
        )
        await state.update_data(resume=resume.to_dict())
        await state.set_state(SkillSearchStates.waiting_for_profession_for_comparison)

    except Exception as e:
        await processing_msg.delete()
        await message.answer(f"Ошибка анализа резюме: {str(e)}")
        await state.clear()


def format_resume_analysis_report(structure: dict, skills: dict, experience: dict, ats: dict, target_position: str) -> str:
    """Сформировать отчет по локальному анализу резюме."""
    message = f"=== УГЛУБЛЕННЫЙ АНАЛИЗ ДЛЯ: {target_position.upper()} ===\n\n"

    message += "=== СТРУКТУРА РЕЗЮМЕ ===\n"
    message += f"Оценка структуры: {structure.get('structure_score', 'N/A')}/10\n"
    message += f"Оценка организации: {structure.get('organization_score', 'N/A')}/10\n"

    missing_sections = structure.get('missing_sections', [])
    if missing_sections:
        message += f"Отсутствующие секции: {', '.join(missing_sections)}\n"

    message += "\n=== АНАЛИЗ НАВЫКОВ ===\n"
    message += f"Релевантность: {skills.get('relevance_score', 'N/A')}/10\n"
    message += f"Презентация: {skills.get('presentation_score', 'N/A')}/10\n"
    message += f"Релевантность заголовка: {skills.get('title_fit_score', 'N/A')}/10\n"
    message += f"SEO под HH: {skills.get('hh_seo_score', 'N/A')}/10\n"

    missing_critical = skills.get('missing_critical', [])
    if missing_critical:
        message += f"Критичные отсутствующие навыки: {', '.join(missing_critical[:5])}\n"

    outdated_skills = skills.get('outdated_skills', [])
    if outdated_skills:
        message += f"Устаревшие навыки: {', '.join(outdated_skills[:3])}\n"

    message += "\n=== КАЧЕСТВО ОПЫТА ===\n"
    message += f"Фокус на достижениях: {experience.get('achievement_focus', 'N/A')}/10\n"
    message += f"Измеримые результаты: {experience.get('quantifiable_results', 'N/A')}/10\n"
    message += f"Глаголы действия: {experience.get('action_verbs', 'N/A')}/10\n"
    message += f"Технические детали: {experience.get('technical_detail', 'N/A')}/10\n"
    message += f"Общее впечатление: {experience.get('overall_impact', 'N/A')}/10\n"

    message += "\n=== ATS-ФИЛЬТРЫ ===\n"
    message += f"Общий ATS score: {ats.get('ats_score', 'N/A')}/10\n"
    message += f"Полнота секций: {ats.get('section_completeness_score', 'N/A')}/10\n"
    message += f"Парсинг и читаемость для ATS: {ats.get('parser_friendliness_score', 'N/A')}/10\n"
    message += f"Покрытие ключевых слов: {ats.get('keyword_coverage_score', 'N/A')}/10\n"
    message += f"Совпадение заголовка: {ats.get('title_match_score', 'N/A')}/10\n"
    message += f"Размещение ключевых слов: {ats.get('keyword_placement_score', 'N/A')}/10\n"
    message += f"Общая читабельность: {ats.get('readability_score', 'N/A')}/10\n"

    all_recommendations = []
    all_recommendations.extend(structure.get('recommendations', []))
    all_recommendations.extend(skills.get('recommendations', []))
    all_recommendations.extend(experience.get('improvements', []))
    all_recommendations.extend(ats.get('recommendations', []))

    if all_recommendations:
        message += "\n=== ГЛАВНЫЕ РЕКОМЕНДАЦИИ ===\n"
        for index, recommendation in enumerate(all_recommendations[:8], 1):
            message += f"{index}. {recommendation}\n"

    structure_score = structure.get('structure_score', 5)
    skills_score = skills.get('relevance_score', 5)
    experience_score = experience.get('overall_impact', 5)
    overall_score = round((structure_score + skills_score + experience_score) / 3, 1)

    message += f"\n=== ОБЩАЯ ОЦЕНКА: {overall_score}/10 ===\n"

    if overall_score >= 8:
        message += "Отличное резюме! Высокая конкурентоспособность.\n"
    elif overall_score >= 6:
        message += "Хорошее резюме с возможностями для улучшения.\n"
    elif overall_score >= 4:
        message += "Среднее резюме. Требуются значительные улучшения.\n"
    else:
        message += "Резюме требует серьезной доработки.\n"

    return message
