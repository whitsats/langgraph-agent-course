"""
mvp_crew.py — MVP Mode Crew v3.0 (Red-Blue Confrontation Support)
==================================================================
Changes from v2.1:
- ReworkCrew added: runs only mvp_scaffolding → mvp_debug → mvp_qa.
  Skips BA interview to avoid re-paying the 3-5 turn token cost on each rework.
  Receives QA feedback via error_context and round_num inputs.
- MvpCrew: unchanged agent/task definitions.
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
from typing import Any
import os


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
# Shared agent factories (reused by both MvpCrew and ReworkCrew)
# ---------------------------------------------------------------------------

def _read_tools():
    return [FileReadTool(), CheckpointValidatorTool()]

def _write_tools():
    return [FileReadTool(), CheckpointValidatorTool(), ProjectScaffolderTool()]

def _guard_tools():
    return [FileReadTool(), CheckpointValidatorTool(), ProjectScaffolderTool(), ScopeGuardTool()]


# ---------------------------------------------------------------------------
# MvpCrew — Full cycle (BA interview + Dev + DevOps + QA)
# ---------------------------------------------------------------------------

@CrewBase
class MvpCrew:
    """MVP Full Cycle Crew: boundary → requirements → scaffold → deploy → QA."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def ba(self) -> Agent:
        return Agent(
            config=self.agents_config["ba"],  # type: ignore[index]
            tools=_write_tools(),
            llm=LLMFactory.create_llm("standard"),
            verbose=True,
            reasoning=False,
            max_iter=100,
        )

    @agent
    def fullstack_dev(self) -> Agent:
        return Agent(
            config=self.agents_config["fullstack_dev"],  # type: ignore[index]
            tools=_write_tools(),
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
            llm=LLMFactory.create_llm("operator"),
            verbose=True,
            reasoning=False,
            max_iter=30,
        )

    @agent
    def qa_engineer(self) -> Agent:
        return Agent(
            config=self.agents_config["qa_engineer"],  # type: ignore[index]
            tools=[DockerMCPTool(), FileReadTool(), CheckpointValidatorTool(), ProjectScaffolderTool()],
            llm=LLMFactory.create_llm("operator"),
            verbose=True,
            reasoning=False,
            max_iter=100,
        )

    @agent
    def code_reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["code_reviewer"],  # type: ignore[index]
            tools=_write_tools(),
            llm=LLMFactory.create_llm("standard"),
            verbose=True,
            reasoning=False,
            max_iter=30,
        )

    @task
    def mvp_boundary_task(self) -> Task:
        return Task(
            config=self.tasks_config["mvp_boundary_task"],  # type: ignore[index]
            human_input=True,
        )

    @task
    def mvp_requirements_task(self) -> Task:
        return Task(
            config=self.tasks_config["mvp_requirements_task"],  # type: ignore[index]
            context=[self.mvp_boundary_task()],
        )

    @task
    def mvp_scaffolding_task(self) -> Task:
        return Task(
            config=self.tasks_config["mvp_scaffolding_task"],  # type: ignore[index]
            context=[self.mvp_requirements_task()],
        )

    @task
    def mvp_review_task(self) -> Task:
        return Task(
            config=self.tasks_config["mvp_review_task"],  # type: ignore[index]
            context=[self.mvp_scaffolding_task()],
        )

    @task
    def mvp_debug_task(self) -> Task:
        return Task(
            config=self.tasks_config["mvp_debug_task"],  # type: ignore[index]
            context=[self.mvp_review_task()],
        )

    @task
    def mvp_qa_task(self) -> Task:
        return Task(
            config=self.tasks_config["mvp_qa_task"],  # type: ignore[index]
            context=[self.mvp_debug_task()],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            step_callback=thought_callback,
        )


# ---------------------------------------------------------------------------
# ReworkCrew — Abbreviated cycle (skip BA, run Dev → DevOps → QA only)
#
# Design rationale:
#   On rework rounds, the BA interview is expensive (3-5 turns) and its
#   output (boundary_manifest.md + requirements.md) already exists on disk.
#   ReworkCrew reads those files and re-runs only the engineering triangle:
#   fullstack_dev fixes code (informed by QA error_context),
#   devops redeploys, qa_engineer re-attacks.
# ---------------------------------------------------------------------------

@CrewBase
class ReworkCrew:
    """
    Rework Cycle Crew: fix code → redeploy → QA re-attack.
    Used for Round 2+ of the Red-Blue confrontation.
    Reads existing requirements.md and tech_specs.md from disk;
    does NOT run the BA interview again.
    """

    agents_config = "config/agents.yaml"
    tasks_config = "config/rework_tasks.yaml"   # Separate YAML, no 'ba' agent referenced

    @agent
    def fullstack_dev(self) -> Agent:
        return Agent(
            config=self.agents_config["fullstack_dev"],  # type: ignore[index]
            tools=_write_tools(),
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
            llm=LLMFactory.create_llm("operator"),
            verbose=True,
            reasoning=False,
            max_iter=30,
        )

    @agent
    def qa_engineer(self) -> Agent:
        return Agent(
            config=self.agents_config["qa_engineer"],  # type: ignore[index]
            tools=[DockerMCPTool(), FileReadTool(), CheckpointValidatorTool(), ProjectScaffolderTool()],
            llm=LLMFactory.create_llm("operator"),
            verbose=True,
            reasoning=False,
            max_iter=100,
        )

    @agent
    def code_reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["code_reviewer"],  # type: ignore[index]
            tools=_write_tools(),
            llm=LLMFactory.create_llm("standard"),
            verbose=True,
            reasoning=False,
            max_iter=30,
        )

    @task
    def rework_scaffolding_task(self) -> Task:
        return Task(
            config=self.tasks_config["rework_scaffolding_task"],  # type: ignore[index]
        )

    @task
    def rework_review_task(self) -> Task:
        return Task(
            config=self.tasks_config["rework_review_task"],  # type: ignore[index]
            context=[self.rework_scaffolding_task()],
        )

    @task
    def rework_debug_task(self) -> Task:
        return Task(
            config=self.tasks_config["rework_debug_task"],  # type: ignore[index]
            context=[self.rework_review_task()],
        )

    @task
    def rework_qa_task(self) -> Task:
        return Task(
            config=self.tasks_config["rework_qa_task"],  # type: ignore[index]
            context=[self.rework_debug_task()],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            step_callback=thought_callback,
        )

