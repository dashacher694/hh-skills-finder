import re
from typing import Optional, List
from pathlib import Path
import pdfplumber
from docx import Document

from src.core.resume_models import Resume, Education, WorkExperience


class ResumeParser:
    
    def __init__(self):
        pass
    
    async def parse_file(self, file_path: str) -> Resume:
        path = Path(file_path)
        
        if path.suffix.lower() == '.pdf':
            return await self._parse_pdf(file_path)
        elif path.suffix.lower() in ['.docx', '.doc']:
            return await self._parse_docx(file_path)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")
    
    async def _parse_pdf(self, file_path: str) -> Resume:
        text = ""
        
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        return self._extract_data(text)
    
    async def _parse_docx(self, file_path: str) -> Resume:
        doc = Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return self._extract_data(text)
    
    def _extract_data(self, text: str) -> Resume:
        resume = Resume(raw_text=text)
        
        resume.name = self._extract_name(text)
        resume.position = self._extract_position(text)
        resume.skills = self._extract_skills(text)
        resume.work_experience = self._extract_work_experience(text)
        resume.education = self._extract_education(text)
        resume.total_experience_years = self._extract_experience_from_header(text)
        
        return resume
    
    def _extract_experience_from_header(self, text: str) -> Optional[float]:
        search_text = text[:500]
        
        match = re.search(r'[Оо]пыт\s+работы\s*[—–-]\s*(\d+)\s*(?:лет|год)', search_text, re.IGNORECASE)
        
        if match:
            years = int(match.group(1))
            
            months_match = re.search(r'[Оо]пыт\s+работы\s*[—–-]\s*\d+\s*(?:лет|год)\s*(\d+)\s*месяц', search_text, re.IGNORECASE)
            
            if months_match:
                months = int(months_match.group(1))
                return round(years + months / 12.0, 1)
            
            return float(years)
        
        return None
    
    def _extract_name(self, text: str) -> Optional[str]:
        lines = text.split('\n')
        for line in lines[:5]:
            line = line.strip()
            if len(line) > 3 and len(line) < 50:
                words = line.split()
                if 2 <= len(words) <= 4 and all(word[0].isupper() for word in words if word):
                    return line
        return None
    
    def _extract_position(self, text: str) -> Optional[str]:
        position_keywords = [
            'developer', 'разработчик', 'engineer', 'инженер',
            'analyst', 'аналитик', 'manager', 'менеджер',
            'designer', 'дизайнер', 'architect', 'архитектор'
        ]
        
        lines = text.split('\n')
        for line in lines[:10]:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in position_keywords):
                if len(line) < 100:
                    return line.strip()
        
        return None
    
    def _extract_skills(self, text: str) -> List[str]:
        found_skills = set()
        
        skill_section = re.search(
            r'Навыки\s*\n(.*?)(?=\nЗнание языков|\nДополнительная информация|\nОбо мне|$)',
            text,
            re.IGNORECASE | re.DOTALL
        )
        
        if skill_section:
            skills_text = skill_section.group(1)
            skill_items = re.findall(r'([A-Za-zА-Яа-я0-9\s\.\-/#+()]+?)(?:\s{2,}|\n)', skills_text)
            
            for skill in skill_items:
                skill = skill.strip()
                if 2 < len(skill) < 50 and skill.lower() not in ['русский', 'английский', 'родной', 'средний', 'b1', 'b2', 'c1']:
                    found_skills.add(skill)
        
        stacks = re.findall(r'[Сс]тек:\s*([^\n]+)', text)
        for stack in stacks:
            skills = re.split(r'[,;]\s*', stack)
            for skill in skills:
                skill = skill.strip()
                if 2 < len(skill) < 50:
                    found_skills.add(skill)
        
        return sorted(list(found_skills))[:30]
    
    def _extract_education(self, text: str) -> List[Education]:
        educations = []
        
        edu_section = re.search(
            r'(?:образование|education)[:\s]+(.*?)(?=опыт|experience|навыки|skills|$)',
            text,
            re.IGNORECASE | re.DOTALL
        )
        
        if edu_section:
            edu_text = edu_section.group(1)
            
            university_keywords = [
                'университет', 'university', 'институт', 'institute',
                'академия', 'academy', 'колледж', 'college'
            ]
            
            lines = edu_text.split('\n')
            for line in lines:
                line = line.strip()
                if any(keyword in line.lower() for keyword in university_keywords):
                    if len(line) > 5 and len(line) < 200:
                        edu = Education(institution=line)
                        educations.append(edu)
                        if len(educations) >= 3:
                            break
        
        return educations
    
    def _extract_work_experience(self, text: str) -> List[WorkExperience]:
        return []
    
    def _calculate_total_experience(self, experiences: List[WorkExperience]) -> Optional[float]:
        return None
