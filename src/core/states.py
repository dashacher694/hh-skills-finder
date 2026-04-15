from aiogram.fsm.state import State, StatesGroup


class SkillSearchStates(StatesGroup):
    waiting_for_profession = State()
    waiting_for_vacancy_count = State()
