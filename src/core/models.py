from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Skill:
    name: str
    count: int
    
    def __str__(self) -> str:
        return f"{self.name} ({self.count})"


@dataclass
class SalaryInfo:
    min_salary: Optional[int]
    max_salary: Optional[int]
    currency: Optional[str]
    
    @property
    def average(self) -> Optional[int]:
        if self.min_salary and self.max_salary:
            return (self.min_salary + self.max_salary) // 2
        return self.min_salary or self.max_salary


@dataclass
class VacancyInfo:
    id: str
    title: str
    skills: List[str]
    salary: Optional[SalaryInfo] = None
    experience: Optional[str] = None


@dataclass
class ExperienceStats:
    no_experience: int = 0
    between_1_and_3: int = 0
    between_3_and_6: int = 0
    more_than_6: int = 0
    
    @property
    def most_common(self) -> str:
        stats = {
            "Без опыта": self.no_experience,
            "1-3 года": self.between_1_and_3,
            "3-6 лет": self.between_3_and_6,
            "Более 6 лет": self.more_than_6
        }
        if not any(stats.values()):
            return "Не указано"
        return max(stats.items(), key=lambda x: x[1])[0]


@dataclass
class SalaryStats:
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    avg_salary: Optional[int] = None
    median_salary: Optional[int] = None
    currency: str = "RUR"
    vacancies_with_salary: int = 0
    
    def format_salary(self, amount: Optional[int]) -> str:
        if amount is None:
            return "Не указано"
        if self.currency == "RUR":
            return f"{amount:,} ₽".replace(",", " ")
        return f"{amount:,} {self.currency}".replace(",", " ")


@dataclass
class SkillAnalysisResult:
    profession: str
    total_vacancies: int
    top_skills: List[Skill]
    salary_stats: Optional[SalaryStats] = None
    experience_stats: Optional[ExperienceStats] = None
    
    def format_message(self) -> str:
        if not self.top_skills:
            return f"По запросу '{self.profession}' навыки не найдены."
        
        message = f"Анализ для профессии: {self.profession}\n"
        message += f"Проанализировано вакансий: {self.total_vacancies}\n\n"
        
        if self.salary_stats and self.salary_stats.vacancies_with_salary > 0:
            message += "=== ЗАРПЛАТА ===\n"
            message += f"Средняя: {self.salary_stats.format_salary(self.salary_stats.avg_salary)}\n"
            message += f"Медианная: {self.salary_stats.format_salary(self.salary_stats.median_salary)}\n"
            message += f"Диапазон: {self.salary_stats.format_salary(self.salary_stats.min_salary)} - {self.salary_stats.format_salary(self.salary_stats.max_salary)}\n"
            message += f"Вакансий с указанной зарплатой: {self.salary_stats.vacancies_with_salary}/{self.total_vacancies}\n\n"
        
        if self.experience_stats:
            message += "=== ТРЕБУЕМЫЙ ОПЫТ ===\n"
            message += f"Чаще всего требуют: {self.experience_stats.most_common}\n"
            message += f"Без опыта: {self.experience_stats.no_experience} вакансий\n"
            message += f"1-3 года: {self.experience_stats.between_1_and_3} вакансий\n"
            message += f"3-6 лет: {self.experience_stats.between_3_and_6} вакансий\n"
            message += f"Более 6 лет: {self.experience_stats.more_than_6} вакансий\n\n"
        
        message += "=== ТОП-15 НАВЫКОВ ===\n"
        for idx, skill in enumerate(self.top_skills, 1):
            message += f"{idx}. {skill.name} — упоминаний: {skill.count}\n"
        
        return message
