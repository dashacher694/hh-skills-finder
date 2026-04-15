from aiogram.fsm.state import State, StatesGroup


class SkillSearchStates(StatesGroup):
    waiting_for_profession = State()
    waiting_for_vacancy_count = State()
    waiting_for_resume = State()
    waiting_for_profession_for_comparison = State()
    waiting_for_resume_analysis_target = State()
