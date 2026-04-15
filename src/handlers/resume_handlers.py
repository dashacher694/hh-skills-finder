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

SKILL_ALIASES = {
    "django framework": "django",
    "rest api": "api",
    "http api": "api",
    "ооп": "oop",
    "oop": "oop",
    "gitlab ci": "ci/cd",
    "github actions": "ci/cd",
    "postgres": "postgresql",
    "postgre": "postgresql",
    "ms sql": "sql",
    "mysql": "sql",
    "rabbitmq": "message broker",
    "kafka": "message broker",
    "faststream (kafka)": "message broker",
    "faststream": "message broker",
    "gitlab": "git",
    "github": "git",
    "алгоритмы и структуры данных": "computer science fundamentals",
    "алгоритмы": "computer science fundamentals",
    "структуры данных": "computer science fundamentals",
}


def _normalize_skill(skill: str) -> str:
    normalized = skill.strip().lower().replace("ё", "е")
    normalized = " ".join(normalized.split())
    return SKILL_ALIASES.get(normalized, normalized)


def _skill_weight(index: int) -> int:
    if index < 5:
        return 3
    if index < 10:
        return 2
    return 1


def _extract_keyword_evidence(raw_text: str, skill: str) -> bool:
    return _normalize_skill(skill) in _normalize_skill(raw_text)


def _tokenize_text(text: str) -> list[str]:
    normalized = _normalize_skill(text)
    for separator in [",", ".", "/", "|", "(", ")", "-", ":", ";"]:
        normalized = normalized.replace(separator, " ")
    return [part for part in normalized.split() if len(part) > 1]


@router.message(Command("upload_resume"))
async def handle_upload_resume(message: Message, state: FSMContext):
    await state.clear()
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
            "Следующий шаг: сейчас введите название профессии, чтобы сравнить резюме с рынком.\n\n"
            "Примеры:\n"
            "python developer\n"
            "backend разработчик\n"
            "data analyst\n\n"
            "Доступные команды на этом этапе:\n"
            "/analyze_resume - углубленный анализ резюме\n"
            "/upload_resume - загрузить другое резюме"
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


@router.message(SkillSearchStates.waiting_for_profession_for_comparison, F.text & ~F.text.startswith("/"))
async def compare_with_market(message: Message, state: FSMContext):
    profession = message.text.strip()

    if not profession:
        await message.answer(
            "Введите название профессии для анализа рынка.\n\n"
            "Примеры:\n"
            "python developer\n"
            "backend разработчик\n"
            "data analyst"
        )
        return

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
        if not market_skills:
            await processing_msg.delete()
            await message.answer(
                f"Не удалось получить достаточно данных по профессии '{profession}'.\n"
                "Попробуйте уточнить запрос или указать более распространенное название должности."
            )
            return
        
        normalized_resume_skills = {_normalize_skill(skill): skill for skill in resume.skills}
        normalized_market_skills = []
        matched_market_skills = []
        missing_market_skills = []
        total_weight = 0
        matched_weight = 0

        for idx, skill in enumerate(market_analysis.top_skills):
            normalized_market_skill = _normalize_skill(skill.name)
            normalized_market_skills.append(normalized_market_skill)
            weight = _skill_weight(idx)
            total_weight += weight

            if normalized_market_skill in normalized_resume_skills:
                matched_weight += weight
                matched_market_skills.append((skill.name.lower(), skill.count))
            else:
                missing_market_skills.append((skill.name.lower(), skill.count))

        matching_skills = [skill_name for skill_name, _ in matched_market_skills]
        missing_skills = [skill_name for skill_name, _ in missing_market_skills]

        weighted_skill_score = round((matched_weight / total_weight) * 10, 1) if total_weight else 0

        market_skill_counter = Counter(normalized_market_skills)
        core_market_skills = [skill for skill, _ in market_skill_counter.most_common(5)]
        covered_core_skills = [skill for skill in core_market_skills if skill in normalized_resume_skills]
        core_skill_score = round((len(covered_core_skills) / max(len(core_market_skills), 1)) * 10, 1)

        title_tokens = set(_tokenize_text(resume.position or ""))
        profession_tokens = set(_tokenize_text(profession))
        title_hits = len(title_tokens.intersection(profession_tokens))
        title_score = round((title_hits / max(len(profession_tokens), 1)) * 10, 1) if profession_tokens else 4.0

        evidence_hits = 0
        evidence_targets = matching_skills[:8]
        for skill_name in evidence_targets:
            if _extract_keyword_evidence(resume.raw_text.lower(), skill_name):
                evidence_hits += 1
        evidence_score = round((evidence_hits / max(len(evidence_targets), 1)) * 10, 1) if evidence_targets else 3.0

        profession_seniority_markers = {token for token in profession_tokens if token in {"junior", "middle", "mid", "senior", "lead", "стажер", "младший", "старший"}}
        resume_seniority_markers = {token for token in title_tokens if token in {"junior", "middle", "mid", "senior", "lead", "стажер", "младший", "старший"}}
        if not profession_seniority_markers:
            seniority_score = 7.0
        elif profession_seniority_markers.intersection(resume_seniority_markers):
            seniority_score = 9.0
        else:
            seniority_score = 4.5

        keyword_placement_targets = matching_skills[:5] + missing_skills[:5]
        placement_hits = 0
        for skill_name in keyword_placement_targets:
            normalized_skill_name = _normalize_skill(skill_name)
            in_title = normalized_skill_name in _normalize_skill(resume.position or "")
            in_skills = normalized_skill_name in normalized_resume_skills
            in_text = _extract_keyword_evidence(resume.raw_text.lower(), skill_name)
            placement_hits += int(in_title) + int(in_skills) + int(in_text)
        max_placement_hits = max(len(keyword_placement_targets) * 3, 1)
        seo_score = round((placement_hits / max_placement_hits) * 10, 1)

        competitiveness_score = round(
            weighted_skill_score * 0.35 +
            core_skill_score * 0.2 +
            title_score * 0.15 +
            evidence_score * 0.15 +
            seniority_score * 0.05 +
            seo_score * 0.1,
            1,
        )

        score_breakdown = {
            "Ключевые навыки рынка": weighted_skill_score,
            "Покрытие core skills": core_skill_score,
            "Релевантность заголовка": title_score,
            "Подтверждение навыков в опыте": evidence_score,
            "Соответствие seniority": seniority_score,
            "SEO под HH": seo_score,
        }
        
        recommendations = []
        if missing_market_skills:
            top_missing = [skill_name for skill_name, _ in missing_market_skills[:5]]
            recommendations.append(
                f"Добавьте в резюме следующие востребованные навыки: {', '.join(top_missing)}"
            )

            top_gap_with_frequency = ", ".join(
                f"{skill_name} ({count})" for skill_name, count in missing_market_skills[:3]
            )
            recommendations.append(
                f"На рынке особенно часто встречаются: {top_gap_with_frequency}"
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
        
        title_lower = (resume.position or "").lower()
        if not resume.position or len(resume.position) < 10 or title_score < 6:
            recommendations.append(
                f"Оптимизируйте заголовок резюме. Используйте формат: '{profession} | {', '.join(matching_skills[:3])}'"
            )

        if len(matching_skills) < 3:
            recommendations.append(
                "Добавьте в резюме больше ключевых слов из вакансий: они влияют на видимость резюме в поиске HH."
            )

        if title_score < 6:
            recommendations.append(
                f"Сделайте заголовок ближе к рынку: используйте формулировку вроде '{profession} | Python, FastAPI, PostgreSQL'."
            )

        if evidence_score < 6:
            recommendations.append(
                "Часть навыков указана слабо: добавьте их прямо в описания проектов и достижений, а не только в блок навыков."
            )

        if core_skill_score < 6:
            recommendations.append(
                "У вас не закрыты базовые группы навыков для роли. Усильте стек по направлениям: framework, БД, delivery и интеграции."
            )
        
        analysis = ResumeAnalysis(
            resume=resume,
            market_skills=normalized_market_skills,
            missing_skills=missing_skills,
            matching_skills=matching_skills,
            competitiveness_score=competitiveness_score,
            recommendations=recommendations,
            score_breakdown=score_breakdown,
        )
        
        await processing_msg.delete()
        await message.answer(analysis.format_report())
        
        if market_analysis.salary_stats and market_analysis.salary_stats.avg_salary:
            salary_msg = f"\nСредняя зарплата на рынке: {market_analysis.salary_stats.format_salary(market_analysis.salary_stats.avg_salary)}"
            await message.answer(salary_msg)

        await message.answer(
            "Вы можете:\n"
            "/analyze_resume - получить углубленный анализ резюме\n"
            "/upload_resume - загрузить другое резюме"
        )
        
    except Exception as e:
        await processing_msg.delete()
        await message.answer(
            f"Произошла ошибка при анализе: {str(e)}\n"
            "Попробуйте позже."
        )
        await state.clear()


@router.message(SkillSearchStates.waiting_for_resume)
async def invalid_resume_file(message: Message):
    await message.answer(
        "Пожалуйста, загрузите файл резюме в формате PDF или Word.\n"
        "Используйте кнопку прикрепления файла."
    )
