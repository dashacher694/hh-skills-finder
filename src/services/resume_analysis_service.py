from collections import Counter
from typing import Dict, List

from src.core.resume_models import Resume


SKILL_ALIASES = {
    "django framework": "django",
    "rest api": "api",
    "http api": "api",
    "ооп": "oop",
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


class ResumeAnalysisService:
    def __init__(self):
        self._summary_markers = ["обо мне", "about me", "summary", "profile", "цель"]
        self._achievement_markers = [
            "увелич",
            "сниз",
            "оптимиз",
            "улучш",
            "автоматиз",
            "внедр",
            "разработал",
            "разработала",
            "%",
        ]
        self._responsibility_markers = [
            "поддержка",
            "сопровождение",
            "участие",
            "взаимодействие",
            "ведение",
            "работа с",
        ]
        self._action_verbs = [
            "разработал",
            "разработала",
            "внедрил",
            "внедрила",
            "оптимизировал",
            "оптимизировала",
            "создал",
            "создала",
            "автоматизировал",
            "автоматизировала",
        ]

    async def analyze_resume_structure(self, resume: Resume) -> Dict:
        missing_sections: List[str] = []
        recommendations: List[str] = []
        text_lower = resume.raw_text.lower()

        if not resume.name:
            missing_sections.append("Имя")
        if not resume.position:
            missing_sections.append("Желаемая должность")
        if not resume.skills:
            missing_sections.append("Навыки")
        if not resume.total_experience_years:
            missing_sections.append("Опыт работы")
        if not resume.education:
            missing_sections.append("Образование")
        if not self._has_summary(resume):
            missing_sections.append("Блок 'О себе'")

        structure_score = max(10 - len(missing_sections), 1)
        organization_score = 8 if len(resume.raw_text.splitlines()) > 10 else 5

        if len(resume.skills) < 8:
            organization_score = max(organization_score - 1, 1)
        if text_lower.count("стек:") >= 2 or text_lower.count("навыки") >= 2:
            structure_score = min(structure_score + 1, 10)

        if "Блок 'О себе'" in missing_sections:
            recommendations.append("Добавьте короткий блок 'О себе' с позиционированием и ключевой экспертизой")
        if "Навыки" in missing_sections:
            recommendations.append("Добавьте отдельный блок с ключевыми навыками")
        if "Желаемая должность" in missing_sections:
            recommendations.append("Уточните заголовок резюме под целевую должность")
        if not recommendations:
            recommendations.append("Структура резюме в целом хорошая, но можно усилить читаемость короткими смысловыми блоками")

        return {
            "structure_score": structure_score,
            "missing_sections": missing_sections,
            "organization_score": organization_score,
            "recommendations": recommendations,
        }

    async def analyze_skills_relevance(self, resume: Resume, target_position: str) -> Dict:
        normalized_target_words = self._normalize_text_tokens(target_position)
        normalized_skills = [self._normalize_skill(skill) for skill in resume.skills]
        normalized_skills_set = set(normalized_skills)
        outdated_skills = [skill for skill in resume.skills if skill.strip().endswith(".")]
        recommendations: List[str] = []

        title_text = self._normalize_text(resume.position or "")
        raw_text_lower = self._normalize_text(resume.raw_text)

        inferred_keywords = [word for word in normalized_target_words if len(word) > 2]
        if not inferred_keywords:
            inferred_keywords = list(normalized_skills_set)[:5]

        matched_keywords = [keyword for keyword in inferred_keywords if keyword in normalized_skills_set or keyword in raw_text_lower]
        missing_keywords = [keyword for keyword in inferred_keywords if keyword not in matched_keywords]

        relevance_score = round((len(matched_keywords) / max(len(inferred_keywords), 1)) * 10, 1)
        presentation_score = 8 if len(resume.skills) >= 10 else 5

        title_hits = sum(1 for keyword in inferred_keywords if keyword in title_text)
        title_fit_score = round((title_hits / max(len(inferred_keywords), 1)) * 10, 1)

        placement_hits = 0
        tracked_keywords = inferred_keywords[:8] if inferred_keywords else normalized_skills[:8]
        for keyword in tracked_keywords:
            in_title = keyword in title_text
            in_skills = keyword in normalized_skills_set
            in_body = keyword in raw_text_lower
            placement_hits += int(in_title) + int(in_skills) + int(in_body)
        hh_seo_score = round((placement_hits / max(len(tracked_keywords) * 3, 1)) * 10, 1) if tracked_keywords else 4.0

        if missing_keywords:
            recommendations.append(f"Добавьте в резюме релевантные ключевые слова: {', '.join(missing_keywords[:5])}")
        if outdated_skills:
            recommendations.append("Почистите оформление навыков: уберите лишние точки и дубли")
        if not resume.position or len((resume.position or "").split()) < 2:
            recommendations.append("Уточните заголовок резюме, добавив роль и ключевые технологии")
        if title_fit_score < 6:
            recommendations.append("Заголовок резюме недостаточно релевантен поиску HH: добавьте роль и 2-3 ключевые технологии")
        if hh_seo_score < 6:
            recommendations.append("Ключевые слова слабо распределены по резюме: добавьте их в заголовок, навыки и описание опыта")
        if not recommendations:
            recommendations.append("Навыки выглядят релевантно, можно сгруппировать их по категориям для лучшей читаемости")

        return {
            "relevance_score": relevance_score,
            "missing_critical": missing_keywords,
            "outdated_skills": outdated_skills,
            "presentation_score": presentation_score,
            "title_fit_score": title_fit_score,
            "hh_seo_score": hh_seo_score,
            "recommendations": recommendations,
        }

    async def analyze_experience_quality(self, resume: Resume) -> Dict:
        text_lower = resume.raw_text.lower()
        achievement_hits = sum(marker in text_lower for marker in self._achievement_markers)
        responsibility_hits = sum(marker in text_lower for marker in self._responsibility_markers)
        action_hits = sum(marker in text_lower for marker in self._action_verbs)
        metrics_hits = text_lower.count("%") + sum(char.isdigit() for char in resume.raw_text[:3000]) // 10

        achievement_focus = min(achievement_hits + 4, 10)
        quantifiable_results = min(metrics_hits + 3, 10)
        action_verbs = min(action_hits + 4, 10)
        technical_detail = 8 if len(resume.skills) >= 12 else 6 if len(resume.skills) >= 6 else 4
        overall_impact = max(min(round((achievement_focus + quantifiable_results + action_verbs + technical_detail) / 4), 10), 1)
        responsibility_penalty = 2 if responsibility_hits > achievement_hits + 2 else 0
        overall_impact = max(overall_impact - responsibility_penalty, 1)

        improvements: List[str] = []
        if achievement_focus < 7:
            improvements.append("Сместите фокус описания опыта с обязанностей на результаты и вклад")
        if quantifiable_results < 7:
            improvements.append("Добавьте метрики: проценты, сроки, количество сервисов, пользователей или задач")
        if action_verbs < 7:
            improvements.append("Используйте более сильные формулировки: разработала, внедрила, оптимизировала, автоматизировала")
        if technical_detail < 7:
            improvements.append("Усильте опыт конкретикой по стеку, архитектуре и зонам ответственности")
        if responsibility_penalty:
            improvements.append("В опыте слишком много общих обязанностей: замените часть формулировок на конкретные достижения")
        if not improvements:
            improvements.append("Блок опыта выглядит сильным, можно дополнительно усилить его 1-2 самыми заметными достижениями")

        return {
            "achievement_focus": achievement_focus,
            "quantifiable_results": quantifiable_results,
            "action_verbs": action_verbs,
            "technical_detail": technical_detail,
            "overall_impact": overall_impact,
            "improvements": improvements,
        }

    async def analyze_ats_filters(self, resume: Resume, target_position: str) -> Dict:
        normalized_target_words = [word for word in self._normalize_text_tokens(target_position) if len(word) > 2]
        normalized_resume_skills = {self._normalize_skill(skill) for skill in resume.skills}
        normalized_title = self._normalize_text(resume.position or "")
        normalized_text = self._normalize_text(resume.raw_text)

        has_name = bool(resume.name)
        has_title = bool(resume.position)
        has_skills = bool(resume.skills)
        has_experience = bool(resume.total_experience_years)
        has_education = bool(resume.education)
        has_summary = self._has_summary(resume)

        section_hits = sum([has_name, has_title, has_skills, has_experience, has_education, has_summary])
        section_completeness_score = round((section_hits / 6) * 10, 1)

        parseability_checks = [
            len(resume.raw_text) > 300,
            len(resume.raw_text.splitlines()) > 8,
            not any(marker in resume.raw_text for marker in ["\t\t\t", "����"]),
            bool(resume.position),
            bool(resume.skills),
        ]
        parser_friendliness_score = round((sum(parseability_checks) / len(parseability_checks)) * 10, 1)

        keyword_hits = [word for word in normalized_target_words if word in normalized_text or word in normalized_resume_skills]
        keyword_coverage_score = round((len(keyword_hits) / max(len(normalized_target_words), 1)) * 10, 1) if normalized_target_words else 5.0

        title_hits = [word for word in normalized_target_words if word in normalized_title]
        title_match_score = round((len(title_hits) / max(len(normalized_target_words), 1)) * 10, 1) if normalized_target_words else 5.0

        placement_hits = 0
        tracked_keywords = normalized_target_words[:8] if normalized_target_words else list(normalized_resume_skills)[:8]
        for keyword in tracked_keywords:
            in_title = keyword in normalized_title
            in_skills = keyword in normalized_resume_skills
            in_body = keyword in normalized_text
            placement_hits += int(in_title) + int(in_skills) + int(in_body)
        keyword_placement_score = round((placement_hits / max(len(tracked_keywords) * 3, 1)) * 10, 1) if tracked_keywords else 4.0

        average_line_length = round(sum(len(line) for line in resume.raw_text.splitlines()) / max(len(resume.raw_text.splitlines()), 1), 1)
        readability_score = 8.0
        if average_line_length > 120:
            readability_score -= 2
        if len(resume.skills) < 6:
            readability_score -= 1
        if not has_summary:
            readability_score -= 1
        readability_score = max(readability_score, 1.0)

        ats_score = round(
            section_completeness_score * 0.2 +
            parser_friendliness_score * 0.2 +
            keyword_coverage_score * 0.2 +
            title_match_score * 0.15 +
            keyword_placement_score * 0.15 +
            readability_score * 0.1,
            1,
        )

        recommendations: List[str] = []
        if section_completeness_score < 7:
            recommendations.append("Для ATS не хватает обязательных секций: добавьте недостающие блоки и сделайте структуру более полной")
        if parser_friendliness_score < 7:
            recommendations.append("Упростите структуру резюме для парсинга: меньше нестандартного форматирования, больше простых текстовых блоков")
        if keyword_coverage_score < 7:
            recommendations.append("Усильте keyword coverage: добавьте больше терминов из целевой должности и вакансий")
        if title_match_score < 7:
            recommendations.append("Заголовок плохо проходит ATS-фильтр: используйте формулировку ближе к целевой должности")
        if keyword_placement_score < 7:
            recommendations.append("Ключевые слова должны встречаться не только в навыках, но и в заголовке и опыте")
        if readability_score < 7:
            recommendations.append("Повышайте читабельность: короче формулировки, четкие блоки, меньше перегруженных строк")
        if not recommendations:
            recommendations.append("Резюме хорошо выглядит с точки зрения ATS-фильтров")

        return {
            "ats_score": ats_score,
            "section_completeness_score": section_completeness_score,
            "parser_friendliness_score": parser_friendliness_score,
            "keyword_coverage_score": keyword_coverage_score,
            "title_match_score": title_match_score,
            "keyword_placement_score": keyword_placement_score,
            "readability_score": readability_score,
            "recommendations": recommendations,
        }

    def _has_summary(self, resume: Resume) -> bool:
        text_lower = resume.raw_text.lower()
        return any(marker in text_lower for marker in self._summary_markers)

    def _normalize_skill(self, skill: str) -> str:
        normalized = self._normalize_text(skill)
        return SKILL_ALIASES.get(normalized, normalized)

    def _normalize_text(self, text: str) -> str:
        normalized = text.strip().lower().replace("ё", "е")
        return " ".join(normalized.split())

    def _normalize_text_tokens(self, text: str) -> List[str]:
        cleaned = self._normalize_text(text)
        separators = [",", ".", "/", "|", "(", ")", "-", ":"]
        for separator in separators:
            cleaned = cleaned.replace(separator, " ")
        return [part for part in cleaned.split() if part]
