from agent.core.prompts import TIMESHEET_AGENT_SYSTEM_PROMPT
from langchain_core.prompts import PromptTemplate


def test_prompt_indica_usar_subtarea_de_tiempo_personal():
    assert "Tiempo personal" in TIMESHEET_AGENT_SYSTEM_PROMPT
    assert "subtarea" in TIMESHEET_AGENT_SYSTEM_PROMPT


def test_prompt_sigue_siendo_un_template_valido():
    rendered = PromptTemplate.from_template(TIMESHEET_AGENT_SYSTEM_PROMPT).format(
        today_date="2026-11-24"
    )
    assert "2026-11-24" in rendered
