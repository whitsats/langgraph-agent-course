"""
enterprise_crew.py — Enterprise SDLC Crew v2.0
===============================================
Changes from v1.0:
- P0-2: DockerMCPTool updated upstream (compose-only policy).
- P0-3: ScopeGuardTool added to architect, fullstack_dev, backend_dev, frontend_dev.
        ent_scaffolding_task gets scope_guardrail Guardrail.
- P1-3: devops.max_iter reduced 15 -> 8. qa_engineer.max_iter 15 -> 10.
- P2-1: CheckpointValidatorTool added to all agents.
- P2-3: allow_code_execution explicitly False + documented.
- MISC: thought_callback extracted to shared utils.callbacks.
"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.tasks.task_output import TaskOutput
from virtual_rnd_center.tools.project_tools import ProjectScaffolderTool
from virtual_rnd_center.tools.docker_mcp_tool import DockerMCPTool
from virtual_rnd_center.tools.file_read_tool import FileReadTool
from virtual_rnd_center.tools.guard_tools import CheckpointValidatorTool, ScopeGuardTool
from virtual_rnd_center.utils.llm_factory import LLMFactory
from virtual_rnd_center.utils.callbacks import thought_callback
from crewai_tools import SerperDevTool
from typing import Any
import os


# ---------------------------------------------------------------------------
# P0-3: Scope Guardrail (shared pattern with mvp_crew)
# ---------------------------------------------------------------------------

def scope_guardrail(result: TaskOutput) -> tuple[bool, Any]:
    guard = ScopeGuardTool()
    scan_result: str = guard._run(
        content=result.raw,
        manifest_path="output/enterprise_project/requirements.md",
    )
    if "SCOPE_VIOLATION" in scan_result:
        return (False, scan_result)
    return (True, result.raw)


# ---------------------------------------------------------------------------
# Enterprise Crew
# ---------------------------------------------------------------------------

@CrewBase
class EnterpriseCrew:
    """Enterprise SDLC Crew — Milestone-Driven (v2.0)."""

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
    def pm(self) -> Agent:
        return Agent(
            config=self.agents_config["pm"],  # type: ignore[index]
            tools=[SerperDevTool(), FileReadTool(), CheckpointValidatorTool()],
            llm=LLMFactory.create_llm("creative"),  # P1-B: high temp for divergent research
            verbose=True,
            reasoning=False,
            max_iter=100,
        )

    @agent
    def ba(self) -> Agent:
        return Agent(
            config=self.agents_config["ba"],  # type: ignore[index]
            tools=self._write_tools(),
            llm=LLMFactory.create_llm("standard"),
            verbose=True,
            reasoning=False,
            max_iter=100,
        )

    @agent
    def nitpicker(self) -> Agent:
        return Agent(
            config=self.agents_config["nitpicker"],  # type: ignore[index]
            tools=self._read_tools(),
            llm=LLMFactory.create_llm("auditor"),   # P1-B: low temp for reproducible audits
            verbose=True,
            reasoning=False,
            max_iter=100,
        )

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
    def fullstack_dev(self) -> Agent:
        return Agent(
            config=self.agents_config["fullstack_dev"],  # type: ignore[index]
            tools=self._guard_tools(),
            llm=LLMFactory.create_llm("standard"),
            allow_code_execution=False,
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
    def frontend_dev(self) -> Agent:
        return Agent(
            config=self.agents_config["frontend_dev"],  # type: ignore[index]
            tools=self._guard_tools(),
            llm=LLMFactory.create_llm("standard"),
            allow_code_execution=False,
            verbose=True,
            reasoning=False,
            max_iter=100,
        )

    @agent
    def devops(self) -> Agent:
        return Agent(
            config=self.agents_config["devops"],  # type: ignore[index]
            tools=[DockerMCPTool(), ProjectScaffolderTool(), FileReadTool(), CheckpointValidatorTool()],
            llm=LLMFactory.create_llm("operator"),  # P1-B: low temp
            verbose=True,
            reasoning=False,
            max_iter=30,
        )

    @agent
    def qa_engineer(self) -> Agent:
        return Agent(
            config=self.agents_config["qa_engineer"],  # type: ignore[index]
            tools=[DockerMCPTool(), FileReadTool(), CheckpointValidatorTool()],
            llm=LLMFactory.create_llm("operator"),  # P1-B: low temp
            verbose=True,
            reasoning=False,
            max_iter=30,
        )

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    @task
    def ent_research_task(self) -> Task:
        return Task(config=self.tasks_config["ent_research_task"])  # type: ignore[index]

    @task
    def ent_critique_task(self) -> Task:
        return Task(config=self.tasks_config["ent_critique_task"])  # type: ignore[index]

    @task
    def ent_decision_gate(self) -> Task:
        return Task(
            config=self.tasks_config["ent_decision_gate"],  # type: ignore[index]
            human_input=True,
        )

    @task
    def ent_prd_distill(self) -> Task:
        # P1-C: context chain from decision gate
        return Task(
            config=self.tasks_config["ent_prd_distill"],  # type: ignore[index]
            context=[self.ent_decision_gate()],
        )

    @task
    def ent_arch_design(self) -> Task:
        # P1-C: context chain
        return Task(
            config=self.tasks_config["ent_arch_design"],  # type: ignore[index]
            context=[self.ent_prd_distill()],
        )

    @task
    def ent_impl_planning(self) -> Task:
        # P1-C: context chain
        return Task(
            config=self.tasks_config["ent_impl_planning"],  # type: ignore[index]
            context=[self.ent_arch_design()],
            human_input=True,
        )

    @task
    def ent_scaffolding_task(self) -> Task:
        # P0-3: scope guardrail on code generation
        return Task(
            config=self.tasks_config["ent_scaffolding_task"],  # type: ignore[index]
            guardrail=scope_guardrail,
            guardrail_max_retries=2,
        )

    @task
    def ent_integration_debug(self) -> Task:
        return Task(config=self.tasks_config["ent_integration_debug"])  # type: ignore[index]

    @task
    def ent_qa_task(self) -> Task:
        return Task(
            config=self.tasks_config["ent_qa_task"],  # type: ignore[index]
            human_input=True,
        )

    @task
    def ent_code_nitpick_task(self) -> Task:
        return Task(
            config=self.tasks_config["ent_code_nitpick_task"],  # type: ignore[index]
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
