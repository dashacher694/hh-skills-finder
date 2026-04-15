from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class Education:
    institution: str
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    graduation_year: Optional[int] = None


@dataclass
class WorkExperience:
    company: str
    position: str
    description: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration_months: Optional[int] = None


@dataclass
class Resume:
    raw_text: str
    name: Optional[str] = None
    position: Optional[str] = None
    skills: List[str] = field(default_factory=list)
    work_experience: List[WorkExperience] = field(default_factory=list)
    education: List[Education] = field(default_factory=list)
    total_experience_years: Optional[float] = None
    languages: List[str] = field(default_factory=list)
    uploaded_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "raw_text": self.raw_text,
            "name": self.name,
            "position": self.position,
            "skills": self.skills,
            "total_experience_years": self.total_experience_years,
            "languages": self.languages,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Resume":
        resume = cls(
            raw_text=data.get("raw_text", ""),
            name=data.get("name"),
            position=data.get("position"),
            skills=data.get("skills", []),
            total_experience_years=data.get("total_experience_years"),
            languages=data.get("languages", [])
        )
        if data.get("uploaded_at"):
            resume.uploaded_at = datetime.fromisoformat(data["uploaded_at"])
        return resume
    
    def get_all_skills_text(self) -> str:
        return ", ".join(self.skills) if self.skills else "Навыки не указаны"
    
    def get_experience_summary(self) -> str:
        if not self.work_experience and not self.total_experience_years:
            return "Опыт работы не указан"
        
        summary = ""
        if self.work_experience:
            summary += f"Всего мест работы: {len(self.work_experience)}\n"
        
        if self.total_experience_years:
            summary += f"Общий стаж: {self.total_experience_years:.1f} лет\n"
        
        return summary if summary else "Опыт работы не указан"
    
    def format_summary(self) -> str:
        message = "=== АНАЛИЗ РЕЗЮМЕ ===\n\n"
        
        if self.name:
            message += f"Имя: {self.name}\n"
        if self.position:
            message += f"Должность: {self.position}\n"
        
        message += f"\n{self.get_experience_summary()}\n"
        
        if self.skills:
            message += f"\nНайденные навыки ({len(self.skills)}):\n"
            for skill in self.skills[:20]:
                message += f"- {skill}\n"
            if len(self.skills) > 20:
                message += f"... и еще {len(self.skills) - 20}\n"
        
        if self.education:
            message += f"\nОбразование:\n"
            for edu in self.education:
                message += f"- {edu.institution}"
                if edu.degree:
                    message += f" ({edu.degree})"
                message += "\n"
        
        return message


@dataclass
class ResumeAnalysis:
    resume: Resume
    market_skills: List[str]
    missing_skills: List[str]
    matching_skills: List[str]
    competitiveness_score: float
    recommendations: List[str]
    
    def format_report(self) -> str:
        message = "=== СРАВНЕНИЕ С РЫНКОМ ===\n\n"
        
        message += f"Оценка конкурентоспособности: {self.competitiveness_score:.1f}/10\n\n"
        
        if self.matching_skills:
            message += f"Совпадающие навыки ({len(self.matching_skills)}):\n"
            for skill in self.matching_skills[:10]:
                message += f"- {skill}\n"
            message += "\n"
        
        if self.missing_skills:
            message += f"Отсутствующие навыки ({len(self.missing_skills)}):\n"
            for skill in self.missing_skills[:10]:
                message += f"- {skill}\n"
            message += "\n"
        
        if self.recommendations:
            message += "=== РЕКОМЕНДАЦИИ ===\n"
            for idx, rec in enumerate(self.recommendations, 1):
                message += f"{idx}. {rec}\n"
        
        return message
