"""
backend_crew.py — Backend Specialized Crew v2.0
================================================
Changes from v1.0:
- Fixed import: use virtual_rnd_center.tools.file_read_tool (not crewai_tools)
- P0-3: ScopeGuardTool added to architect, backend_dev.
        be_code_task gets scope_guardrail Guardrail.
- P2-1: CheckpointValidatorTool added to all agents.
- P2-3: allow_code_execution=False explicitly documented.
- MISC: thought_callback from shared utils.callbacks.
"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.tasks.task_output import TaskOutput
from virtual_rnd_center.tools.project_tools import ProjectScaffolderTool
from virtual_rnd_center.tools.file_read_tool import FileReadTool
from virtual_rnd_center.tools.guard_tools import CheckpointValidatorTool, ScopeGuardTool
from virtual_rnd_center.utils.llm_factory import LLMFactory
from virtual_rnd_center.utils.callbacks import thought_callback
from typing import Any


# ---------------------------------------------------------------------------
# P0-3: Scope Guardrail
# ---------------------------------------------------------------------------

def scope_guardrail(result: TaskOutput) -> tuple[bool, Any]:
    guard = ScopeGuardTool()
    scan_result: str = guard._run(content=result.raw)
    if "SCOPE_VIOLATION" in scan_result:
        return (False, scan_result)
    return (True, result.raw)


# ---------------------------------------------------------------------------
# Backend Crew
# ---------------------------------------------------------------------------

@CrewBase
class BackendCrew:
    """Backend Specialized Crew — API & Data Layer (v2.0)."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def _read_tools(self):
        return [FileReadTool(), CheckpointValidatorTool()]

    def _write_tools(self):
        return [FileReadTool(), CheckpointValidatorTool(), ProjectScaffolderTool()]

    def _guard_tools(self):
        return [FileReadTool(), CheckpointValidatorTool(), ProjectScaffolderTool(), ScopeGuardTool()]

    # ------------------------------------------------------------------
    # Agents
    # ------------------------------------------------------------------

    @agent
    def architect(self) -> Agent:
        return Agent(
            config=self.agents_config["architect"],  # type: ignore[index]
            tools=self._guard_tools(),
            llm=LLMFactory.create_llm("standard"),
            verbose=True,
            reasoning=False,
            max_iter=100,
        )

    @agent
    def backend_dev(self) -> Agent:
        return Agent(
            config=self.agents_config["backend_dev"],  # type: ignore[index]
            tools=self._guard_tools(),
            llm=LLMFactory.create_llm("standard"),
            allow_code_execution=False,
            verbose=True,
            reasoning=False,
            max_iter=100,
        )

    @agent
    def qa_engineer(self) -> Agent:
        return Agent(
            config=self.agents_config["qa_engineer"],  # type: ignore[index]
            tools=self._read_tools(),
            llm=LLMFactory.create_llm("operator"),  # P1-B: low temp
            verbose=True,
            reasoning=False,
            max_iter=30,
        )

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    @task
    def be_design_task(self) -> Task:
        return Task(config=self.tasks_config["be_design_task"])  # type: ignore[index]

    @task
    def be_planning_task(self) -> Task:
        return Task(
            config=self.tasks_config["be_planning_task"],  # type: ignore[index]
            human_input=True,
        )

    @task
    def be_code_task(self) -> Task:
        # P0-3: scope guardrail; P1-C: context chain
        return Task(
            config=self.tasks_config["be_code_task"],  # type: ignore[index]
            context=[self.be_planning_task()],
            guardrail=scope_guardrail,
            guardrail_max_retries=2,
        )

    @task
    def be_qa_task(self) -> Task:
        return Task(
            config=self.tasks_config["be_qa_task"],  # type: ignore[index]
            human_input=True,
        )

    # ------------------------------------------------------------------
    # Crew
    # ------------------------------------------------------------------

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            step_callback=thought_callback,
        )
