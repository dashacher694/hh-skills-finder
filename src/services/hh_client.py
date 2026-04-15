import asyncio
from typing import List, Optional
import aiohttp
from collections import Counter

from src.core.config import settings
from src.core.models import (
    VacancyInfo, 
    Skill, 
    SkillAnalysisResult, 
    SalaryInfo, 
    SalaryStats, 
    ExperienceStats
)


class HeadHunterClient:
    def __init__(self):
        self.base_url = settings.hh_api_base_url
        self.headers = {"User-Agent": settings.hh_user_agent}
    
    async def search_vacancies(self, query: str, limit: int) -> List[VacancyInfo]:
        vacancies = []
        
        async with aiohttp.ClientSession() as session:
            params = {
                "text": query,
                "per_page": min(limit, 100),
                "search_field": "name",
            }
            
            async with session.get(
                f"{self.base_url}/vacancies",
                params=params,
                headers=self.headers
            ) as response:
                if response.status != 200:
                    return vacancies
                
                data = await response.json()
                vacancy_items = data.get("items", [])
                
                tasks = []
                for item in vacancy_items[:limit]:
                    tasks.append(self._fetch_vacancy_details(session, item["id"], item["name"]))
                
                vacancies = await asyncio.gather(*tasks)
                return [v for v in vacancies if v is not None]
    
    async def _fetch_vacancy_details(
        self, 
        session: aiohttp.ClientSession, 
        vacancy_id: str,
        title: str
    ) -> Optional[VacancyInfo]:
        try:
            async with session.get(
                f"{self.base_url}/vacancies/{vacancy_id}",
                headers=self.headers
            ) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                skills = [skill["name"] for skill in data.get("key_skills", [])]
                
                salary_data = data.get("salary")
                salary = None
                if salary_data:
                    salary = SalaryInfo(
                        min_salary=salary_data.get("from"),
                        max_salary=salary_data.get("to"),
                        currency=salary_data.get("currency")
                    )
                
                experience = data.get("experience", {}).get("id")
                
                return VacancyInfo(
                    id=vacancy_id,
                    title=title,
                    skills=skills,
                    salary=salary,
                    experience=experience
                )
        except Exception:
            return None
    
    def _calculate_salary_stats(self, vacancies: List[VacancyInfo]) -> Optional[SalaryStats]:
        salaries = []
        currency = "RUR"
        
        for vacancy in vacancies:
            if vacancy.salary and vacancy.salary.average:
                salaries.append(vacancy.salary.average)
                if vacancy.salary.currency:
                    currency = vacancy.salary.currency
        
        if not salaries:
            return None
        
        salaries.sort()
        avg_salary = sum(salaries) // len(salaries)
        median_salary = salaries[len(salaries) // 2]
        
        return SalaryStats(
            min_salary=min(salaries),
            max_salary=max(salaries),
            avg_salary=avg_salary,
            median_salary=median_salary,
            currency=currency,
            vacancies_with_salary=len(salaries)
        )
    
    def _calculate_experience_stats(self, vacancies: List[VacancyInfo]) -> ExperienceStats:
        stats = ExperienceStats()
        
        for vacancy in vacancies:
            exp = vacancy.experience
            if exp == "noExperience":
                stats.no_experience += 1
            elif exp == "between1And3":
                stats.between_1_and_3 += 1
            elif exp == "between3And6":
                stats.between_3_and_6 += 1
            elif exp == "moreThan6":
                stats.more_than_6 += 1
        
        return stats
    
    async def analyze_skills(self, profession: str, vacancy_count: int) -> SkillAnalysisResult:
        vacancies = await self.search_vacancies(profession, vacancy_count)
        
        all_skills = []
        for vacancy in vacancies:
            all_skills.extend(vacancy.skills)
        
        if not all_skills:
            return SkillAnalysisResult(
                profession=profession,
                total_vacancies=len(vacancies),
                top_skills=[]
            )
        
        skill_counts = Counter(all_skills)
        top_15 = skill_counts.most_common(15)
        top_skills = [Skill(name=name, count=count) for name, count in top_15]
        
        salary_stats = self._calculate_salary_stats(vacancies)
        experience_stats = self._calculate_experience_stats(vacancies)
        
        return SkillAnalysisResult(
            profession=profession,
            total_vacancies=len(vacancies),
            top_skills=top_skills,
            salary_stats=salary_stats,
            experience_stats=experience_stats
        )
