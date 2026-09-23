"""
main.py — VirtualRndFlow v3.0 (Red-Blue Confrontation Tracking)
================================================================
Major changes from v2.0:
- RED-BLUE TRACKING: ConflictRound model records per-round verdicts from
  Dev (SCOPE_OK/VIOLATION), DevOps (PASSED/FAILED), QA (APPROVED/REJECTED).
- SMART RETRY: quality_gate now reads BOTH deployment_report.md AND
  qa_report.md. QA REJECTED verdict triggers rework with injected QA feedback.
- SPLIT-PHASE REWORK: rework cycles skip the BA interview phase and run
  only the dev→devops→qa subset (via 'rework_path' route), avoiding
  token-expensive re-interviews on every retry.
- CONFRONTATION REPORT: final_report() prints a structured table of all
  confrontation rounds, verdicts, and round outcomes.
- project_subdir always injected in kickoff inputs.
- ASCII-safe throughout.
"""

from crewai.flow.flow import Flow, listen, start, router
from pydantic import BaseModel
from typing import Dict, List, Optional
from virtual_rnd_center.crews.mvp_crew.mvp_crew import MvpCrew, ReworkCrew
from virtual_rnd_center.crews.enterprise_crew.enterprise_crew import EnterpriseCrew
from virtual_rnd_center.crews.backend_crew.backend_crew import BackendCrew
from virtual_rnd_center.crews.frontend_crew.frontend_crew import FrontendCrew
import os
import sys
import shutil
import re
import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')
import datetime


# ---------------------------------------------------------------------------
# Red-Blue Confrontation Models
# ---------------------------------------------------------------------------

class ConflictRound(BaseModel):
    """Records the outcome of one Dev → DevOps → QA confrontation cycle."""
    round_num: int
    dev_verdict: str = "UNKNOWN"        # SCOPE_OK / SCOPE_VIOLATION / UNKNOWN
    devops_verdict: str = "UNKNOWN"     # PASSED / FAILED / UNKNOWN
    qa_verdict: str = "UNKNOWN"         # APPROVED / REJECTED / UNKNOWN
    qa_issues: str = ""                 # Key issues extracted from qa_report
    winner: str = ""                    # BLUE (dev wins) / RED (qa wins) / DRAW
    timestamp: str = ""


class RndState(BaseModel):
    mode: str = "mvp"
    user_input: str = ""
    output: str = ""
    rework_count: int = 0
    max_reworks: int = 3
    last_error_log: str = ""
    project_path: str = ""
    project_subdir: str = ""

    # Phase-level health tracking
    phase_status: Dict[str, str] = {}
    failed_phase: str = ""
    checkpoint_log: List[str] = []

    # Red-Blue Confrontation tracking
    confrontation_rounds: List[ConflictRound] = []
    current_round: int = 0


# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------

class LoggerTee:
    def __init__(self, filename: str):
        self.terminal = sys.stdout
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        self.log = open(filename, "a", encoding="utf-8")
        self.ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        self.log_buffer = ""

    def write(self, message: str):
        try:
            self.terminal.write(message)
        except UnicodeEncodeError:
            self.terminal.write(message.encode(self.terminal.encoding or 'utf-8', 'replace').decode(self.terminal.encoding or 'utf-8'))
        
        # Buffer the message for log file processing
        self.log_buffer += message
        
        # Process complete lines
        if '\n' in self.log_buffer:
            lines = self.log_buffer.split('\n')
            self.log_buffer = lines.pop() # Keep the incomplete line in buffer
            
            for line in lines:
                # Remove ANSI escapes
                clean_line = self.ansi_escape.sub('', line)
                
                # Detect box-drawing characters (U+2500 to U+257F)
                has_boxes = bool(re.search(r'[\u2500-\u257F]', clean_line))
                
                # Strip box-drawing characters
                clean_line = re.sub(r'[\u2500-\u257F]+', '', clean_line)
                
                # Strip trailing whitespaces (UI padding)
                clean_line = clean_line.rstrip()
                
                # If the line was just a UI border (boxes and spaces), skip it entirely
                if has_boxes and not clean_line:
                    continue
                    
                self.log.write(clean_line + "\n")
            
            self.log.flush()

    def flush(self):
        self.terminal.flush()
        if self.log_buffer:
            clean_line = self.ansi_escape.sub('', self.log_buffer)
            clean_line = re.sub(r'[\u2500-\u257F]+', '', clean_line).rstrip()
            if clean_line:
                self.log.write(clean_line + "\n")
            self.log_buffer = ""
        self.log.flush()


_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_THIS_DIR))
_LOG_PATH = os.path.join(_PROJECT_ROOT, "output", "session_audit.log")
os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
sys.stdout = LoggerTee(_LOG_PATH)

_MODE_MAP = {
    "mvp":        "mvp_project",
    "enterprise": "enterprise_project",
    "backend":    "backend_project",
    "frontend":   "frontend_project",
}


# ---------------------------------------------------------------------------
# Flow
# ---------------------------------------------------------------------------

class VirtualRndFlow(Flow[RndState]):

    # ------------------------------------------------------------------
    # Initialize
    # ------------------------------------------------------------------

    @start()
    def initialize(self):
        self.state.mode = os.getenv("RND_MODE", self.state.mode)
        subdir = _MODE_MAP.get(self.state.mode, f"{self.state.mode}_project")
        self.state.project_subdir = subdir
        self.state.project_path = os.path.join(_PROJECT_ROOT, "output", subdir)

        print(
            f"\n{'='*60}\n"
            f"[VIRTUAL R&D CENTER] Mode: {self.state.mode.upper()}\n"
            f"[TARGET] {self.state.project_path}\n"
            f"{'='*60}\n",
            flush=True,
        )
        os.makedirs(self.state.project_path, exist_ok=True)
        # Smart Incremental Protection: Clean up ONLY reports from prior cycles
        for report in ["code_review_report.md", "deployment_report.md", "qa_report.md", "qa_acceptance_report.md"]:
            report_path = os.path.join(self.state.project_path, report)
            if os.path.exists(report_path):
                try:
                    os.remove(report_path)
                except Exception:
                    pass

    @router(initialize)
    def route_mode(self):
        return f"{self.state.mode}_path"

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _build_inputs(self) -> dict:
        return {
            "user_input":     self.state.user_input,
            "project_path":   self.state.project_path,
            "project_subdir": self.state.project_subdir,
            "error_context":  self.state.last_error_log,
            "round_num":      str(self.state.current_round),
        }

    def _sanitize_reports(self, directory: str):
        if not os.path.exists(directory):
            return
        tag_pattern = re.compile(r"<.*?>.*?</.*?>|<.*?>", re.DOTALL)
        for root, _, files in os.walk(directory):
            for fname in files:
                if fname.endswith(".md"):
                    path = os.path.join(root, fname)
                    try:
                        with open(path, "r", encoding="utf-8", errors="replace") as f:
                            content = f.read()
                        if "DSML" in content or "tool_calls" in content:
                            clean = tag_pattern.sub("", content).strip()
                            if not clean:
                                clean = f"# Report Error\nAutomatic cleanup for {fname}."
                            with open(path, "w", encoding="utf-8") as f:
                                f.write(clean)
                    except Exception as e:
                        print(f"  [SANITIZE ERROR] {fname}: {e}", flush=True)

    # ------------------------------------------------------------------
    # Verdict readers
    # ------------------------------------------------------------------

    def _read_verdict_from(self, filename: str, positive_kw: list, negative_kw: list) -> str:
        """
        Generic report reader. Scans filename in project_path for keywords.
        Returns the first matching positive keyword, or first matching negative
        keyword, or 'UNKNOWN'.
        """
        path = os.path.join(self.state.project_path, filename)
        if not os.path.exists(path):
            return "UNKNOWN"
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read().upper()
            for kw in positive_kw:
                if kw.upper() in content:
                    return kw.upper()
            for kw in negative_kw:
                if kw.upper() in content:
                    return kw.upper()
        except Exception:
            pass
        return "UNKNOWN"

    def _read_qa_issues(self) -> str:
        """Extract key issues section from qa_report.md (last 800 chars of issues section)."""
        path = os.path.join(self.state.project_path, "qa_report.md")
        if not os.path.exists(path):
            return ""
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            # Try to find issues section
            for marker in ["## 3.", "## edge", "## issue", "## defect", "## finding"]:
                idx = content.lower().find(marker)
                if idx != -1:
                    return content[idx:idx + 800].strip()
            return content[-800:].strip()
        except Exception:
            return ""

    def _read_scope_verdict(self) -> str:
        """Read the smart Code Reviewer verdict from code_review_report.md."""
        path = os.path.join(self.state.project_path, "code_review_report.md")
        if not os.path.exists(path):
            return "UNKNOWN"
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read().upper()
            if "REVIEW VERDICT: APPROVED" in content:
                return "SCOPE_OK"
            if "REVIEW VERDICT: REJECTED" in content:
                return "SCOPE_VIOLATION"
        except Exception:
            pass
        return "UNKNOWN"

    # ------------------------------------------------------------------
    # Confrontation round recorder
    # ------------------------------------------------------------------

    def _record_round(self) -> ConflictRound:
        """
        Read all three reports and build a ConflictRound record.
        DevOps PASSED + QA APPROVED = Blue wins.
        DevOps FAILED or QA REJECTED = Red wins.
        """
        dev_verdict    = self._read_scope_verdict()
        devops_verdict = self._read_verdict_from(
            "deployment_report.md",
            ["PASSED"], ["FAILED"]
        )
        qa_verdict = self._read_verdict_from(
            "qa_report.md",
            ["APPROVED"], ["REJECTED"]
        )
        qa_issues = self._read_qa_issues()

        # Determine winner
        if dev_verdict == "SCOPE_OK" and devops_verdict == "PASSED" and qa_verdict == "APPROVED":
            winner = "BLUE"   # Dev + DevOps + Review team wins
        elif dev_verdict == "SCOPE_VIOLATION" or devops_verdict == "FAILED" or qa_verdict == "REJECTED":
            winner = "RED"    # QA/Review wins
        else:
            winner = "DRAW"

        round_record = ConflictRound(
            round_num=self.state.current_round,
            dev_verdict=dev_verdict,
            devops_verdict=devops_verdict,
            qa_verdict=qa_verdict,
            qa_issues=qa_issues[:300] if qa_issues else "",
            winner=winner,
            timestamp=datetime.datetime.now().strftime("%H:%M:%S"),
        )
        self.state.confrontation_rounds.append(round_record)
        self._print_round_result(round_record)
        return round_record

    def _print_round_result(self, r: ConflictRound):
        """Print a formatted single-round result box."""
        bar = "-" * 55
        print(f"\n{bar}", flush=True)
        print(f"  [CONFRONTATION ROUND #{r.round_num}]  {r.timestamp}", flush=True)
        print(f"  Dev   : {r.dev_verdict}", flush=True)
        print(f"  DevOps: {r.devops_verdict}", flush=True)
        print(f"  QA    : {r.qa_verdict}", flush=True)
        print(f"  Winner: {'[BLUE TEAM - Dev/DevOps]' if r.winner == 'BLUE' else '[RED TEAM - QA]' if r.winner == 'RED' else '[DRAW]'}", flush=True)
        if r.qa_issues:
            print(f"  Issues: {r.qa_issues[:120]}...", flush=True)
        print(f"{bar}\n", flush=True)

    # ------------------------------------------------------------------
    # MVP full path (Round 1: BA → Dev → DevOps → QA)
    # ------------------------------------------------------------------

    @listen("mvp_path")
    def run_mvp(self):
        self.state.current_round += 1
        print(f"[PHASE] MVP Full Cycle — Round #{self.state.current_round}", flush=True)
        try:
            result = MvpCrew().crew().kickoff(inputs=self._build_inputs())
            self.state.output = result.raw
            self._sanitize_reports(self.state.project_path)
            return result
        except Exception as e:
            print(f"[ERROR] MVP run failed: {e}", flush=True)
            raise

    def _interactive_user_gate(self, round_record: ConflictRound) -> str:
        """
        Interactive User Gate:
        Prompts the developer (航玮) to review the round results, allowing manual override.
        Returns:
            - "rework_path" if rework is triggered.
            - "success_exit" if approved.
        """
        import sys
        if not sys.stdin.isatty():
            # Safe fallback for redirected stdin / non-interactive shells
            print("[人机交互控制门] 检测到非交互式终端，跳过人工决策步骤。", flush=True)
            return ""

        print("\n" + "=" * 60, flush=True)
        print("  【系统决策控制门】需要人工介入审阅", flush=True)
        print("=" * 60, flush=True)
        print(f"  当前重工轮次 : #{self.state.rework_count} / {self.state.max_reworks}", flush=True)
        print(f"  代码审查判定 (Dev)   : {round_record.dev_verdict}", flush=True)
        print(f"  容器部署判定 (DevOps): {round_record.devops_verdict}", flush=True)
        print(f"  接口测试判定 (QA)    : {round_record.qa_verdict}", flush=True)
        print(f"  系统自动裁决结果     : {'【通过】(BLUE胜)' if round_record.winner == 'BLUE' else '【未通过】(RED胜)' if round_record.winner == 'RED' else '【平局】'}", flush=True)
        print("-" * 60, flush=True)
        
        while True:
            print("\n请选择您的操作指令:", flush=True)
            print("  【1】 批准并直接交付 (强行通过成功出口)", flush=True)
            print("  【2】 拒绝并触发重工 (强制下发退回整改)", flush=True)
            print("  【3】 拒绝并注入自定义整改意见 (强制退回 + 航玮自定义指示)", flush=True)
            print("  【4】 遵循系统自动裁决 (按框架默认逻辑继续运行)", flush=True)
            choice = input("请输入操作编号 [1-4]: ").strip()
            
            if choice == "1":
                print("[航玮决策] 手动干预：强行通过交付。正在正常收尾退出...", flush=True)
                round_record.winner = "BLUE"
                return "success_exit"
            elif choice == "2":
                print("[航玮决策] 手动干预：强制拒绝。正在触发下一轮自动化重工整改...", flush=True)
                round_record.winner = "RED"
                return "rework_path"
            elif choice == "3":
                custom_feedback = input("\n请输入您要下发给开发 Agent (Full-stack Rapid Constructor) 的具体整改要求或错误上下文:\n").strip()
                if custom_feedback:
                    self.state.last_error_log = (
                        f"[航玮人工审阅反馈]\n"
                        f"航玮下达的具体整改指令如下:\n{custom_feedback}\n"
                    )
                print("[航玮决策] 手动干预：强制拒绝并注入自定义反馈。正在触发自动化重工...", flush=True)
                round_record.winner = "RED"
                return "rework_path"
            elif choice == "4":
                print("[航玮决策] 决定遵循系统自动化裁决。正在继续运行...", flush=True)
                return ""
            else:
                print("无效的输入编号，请输入 1 到 4 之间的数字。", flush=True)

    @router(run_mvp)
    def quality_gate(self, result):
        """
        Red-Blue Confrontation Gate:
        - Record current round verdicts from all three reports.
        - BLUE wins (DevOps PASSED + QA APPROVED) → success_exit.
        - RED wins (FAILED or REJECTED) + retries remain → rework_path (skip BA).
        - Retries exhausted → force success_exit with confrontation summary.
        """
        round_record = self._record_round()

        # Call interactive decision gate
        user_override = self._interactive_user_gate(round_record)
        if user_override:
            if user_override == "success_exit":
                return "success_exit"
            elif user_override == "rework_path" and self.state.rework_count < self.state.max_reworks:
                self.state.rework_count += 1
                if not self.state.last_error_log or not "[USER AUDIT FEEDBACK]" in self.state.last_error_log:
                    self.state.last_error_log = (
                        f"[ROUND {round_record.round_num} FEEDBACK]\n"
                        f"DevOps: {round_record.devops_verdict}\n"
                        f"QA: {round_record.qa_verdict}\n"
                        f"QA Issues:\n{round_record.qa_issues}\n"
                    )
                return "rework_path"

        if round_record.winner == "BLUE":
            return "success_exit"

        if self.state.rework_count < self.state.max_reworks:
            self.state.rework_count += 1
            if not self.state.last_error_log or not "[USER AUDIT FEEDBACK]" in self.state.last_error_log:
                self.state.last_error_log = (
                    f"[ROUND {round_record.round_num} FEEDBACK]\n"
                    f"DevOps: {round_record.devops_verdict}\n"
                    f"QA: {round_record.qa_verdict}\n"
                    f"QA Issues:\n{round_record.qa_issues}\n"
                )
            print(
                f"[GATE] RED team won Round {round_record.round_num}. "
                f"Triggering rework #{self.state.rework_count}/{self.state.max_reworks}",
                flush=True,
            )
            return "rework_path"

        print("[GATE] Max reworks reached. Closing confrontation.", flush=True)
        return "success_exit"

    # ------------------------------------------------------------------
    # REWORK path (Round 2+: skip BA, run Dev→DevOps→QA only)
    # ------------------------------------------------------------------

    @listen("rework_path")
    def run_rework(self):
        self.state.current_round += 1
        print(
            f"[PHASE] Rework Cycle — Round #{self.state.current_round} "
            f"(Rework #{self.state.rework_count}/{self.state.max_reworks})",
            flush=True,
        )
        try:
            result = ReworkCrew().crew().kickoff(inputs=self._build_inputs())
            self.state.output = result.raw
            self._sanitize_reports(self.state.project_path)
            return result
        except Exception as e:
            print(f"[ERROR] Rework failed: {e}", flush=True)
            raise

    @router(run_rework)
    def rework_gate(self, result):
        """Same verdict logic as quality_gate, routes back to rework_path or exits."""
        round_record = self._record_round()

        # Call interactive decision gate
        user_override = self._interactive_user_gate(round_record)
        if user_override:
            if user_override == "success_exit":
                return "success_exit"
            elif user_override == "rework_path" and self.state.rework_count < self.state.max_reworks:
                self.state.rework_count += 1
                if not self.state.last_error_log or not "[USER AUDIT FEEDBACK]" in self.state.last_error_log:
                    self.state.last_error_log = (
                        f"[ROUND {round_record.round_num} FEEDBACK]\n"
                        f"DevOps: {round_record.devops_verdict}\n"
                        f"QA: {round_record.qa_verdict}\n"
                        f"QA Issues:\n{round_record.qa_issues}\n"
                    )
                return "rework_path"

        if round_record.winner == "BLUE":
            return "success_exit"

        if self.state.rework_count < self.state.max_reworks:
            self.state.rework_count += 1
            if not self.state.last_error_log or not "[USER AUDIT FEEDBACK]" in self.state.last_error_log:
                self.state.last_error_log = (
                    f"[ROUND {round_record.round_num} FEEDBACK]\n"
                    f"DevOps: {round_record.devops_verdict}\n"
                    f"QA: {round_record.qa_verdict}\n"
                    f"QA Issues:\n{round_record.qa_issues}\n"
                )
            print(
                f"[GATE] RED won Round {round_record.round_num}. "
                f"Rework #{self.state.rework_count}/{self.state.max_reworks}",
                flush=True,
            )
            return "rework_path"

        print("[GATE] Max reworks reached. Closing confrontation.", flush=True)
        return "success_exit"

    # ------------------------------------------------------------------
    # Enterprise / Backend / Frontend paths
    # ------------------------------------------------------------------

    @listen("enterprise_path")
    def run_enterprise(self):
        self.state.current_round += 1
        print(f"[PHASE] Enterprise Cycle — Round #{self.state.current_round}", flush=True)
        try:
            result = EnterpriseCrew().crew().kickoff(inputs=self._build_inputs())
            self.state.output = result.raw
            self._sanitize_reports(self.state.project_path)
            return result
        except Exception as e:
            print(f"[ERROR] Enterprise run failed: {e}", flush=True)
            raise

    @router(run_enterprise)
    def enterprise_gate(self, result):
        round_record = self._record_round()
        return "success_exit"

    @listen("backend_path")
    def run_backend(self):
        self.state.current_round += 1
        print(f"[PHASE] Backend Cycle — Round #{self.state.current_round}", flush=True)
        try:
            result = BackendCrew().crew().kickoff(inputs=self._build_inputs())
            self.state.output = result.raw
            self._sanitize_reports(self.state.project_path)
            return result
        except Exception as e:
            print(f"[ERROR] Backend run failed: {e}", flush=True)
            raise

    @router(run_backend)
    def backend_gate(self, result):
        round_record = self._record_round()
        return "success_exit"

    @listen("frontend_path")
    def run_frontend(self):
        self.state.current_round += 1
        print(f"[PHASE] Frontend Cycle — Round #{self.state.current_round}", flush=True)
        try:
            result = FrontendCrew().crew().kickoff(inputs=self._build_inputs())
            self.state.output = result.raw
            self._sanitize_reports(self.state.project_path)
            return result
        except Exception as e:
            print(f"[ERROR] Frontend run failed: {e}", flush=True)
            raise

    @router(run_frontend)
    def frontend_gate(self, result):
        round_record = self._record_round()
        return "success_exit"

    # ------------------------------------------------------------------
    # Final report — full confrontation summary
    # ------------------------------------------------------------------

    @listen("success_exit")
    def final_report(self):
        self._print_confrontation_summary()
        self._write_confrontation_report()
        print(f"\n[DELIVERY] Output: {self.state.project_path}\n", flush=True)

    def _print_confrontation_summary(self):
        """Print a full Red-Blue confrontation summary table."""
        rounds = self.state.confrontation_rounds
        if not rounds:
            return

        blue_wins = sum(1 for r in rounds if r.winner == "BLUE")
        red_wins  = sum(1 for r in rounds if r.winner == "RED")
        draws     = sum(1 for r in rounds if r.winner == "DRAW")

        bar = "=" * 70
        print(f"\n{bar}", flush=True)
        print("  RED-BLUE CONFRONTATION SUMMARY", flush=True)
        print(f"  Mode: {self.state.mode.upper()} | Total Rounds: {len(rounds)}", flush=True)
        print(f"  Blue Team (Dev+DevOps) wins: {blue_wins}", flush=True)
        print(f"  Red  Team (QA)         wins: {red_wins}", flush=True)
        print(f"  Draws:                       {draws}", flush=True)
        print(f"  Final Outcome: {'DELIVERED' if blue_wins > red_wins else 'QA HELD'}", flush=True)
        print(bar, flush=True)
        print(f"  {'Rnd':<5} {'Time':<10} {'Dev':<16} {'DevOps':<10} {'QA':<12} {'Winner'}", flush=True)
        print(f"  {'-'*5} {'-'*10} {'-'*16} {'-'*10} {'-'*12} {'-'*10}", flush=True)
        for r in rounds:
            print(
                f"  {r.round_num:<5} {r.timestamp:<10} {r.dev_verdict:<16} "
                f"{r.devops_verdict:<10} {r.qa_verdict:<12} {r.winner}",
                flush=True,
            )
        print(f"{bar}\n", flush=True)

    def _write_confrontation_report(self):
        """Write confrontation summary to output/confrontation_report.md."""
        rounds = self.state.confrontation_rounds
        if not rounds:
            return

        blue_wins = sum(1 for r in rounds if r.winner == "BLUE")
        red_wins  = sum(1 for r in rounds if r.winner == "RED")

        lines = [
            "# Red-Blue Confrontation Report",
            f"",
            f"- **Mode**: {self.state.mode.upper()}",
            f"- **Total Rounds**: {len(rounds)}",
            f"- **Blue Team Wins**: {blue_wins}",
            f"- **Red Team Wins**: {red_wins}",
            f"- **Final Outcome**: {'DELIVERED' if blue_wins > red_wins else 'QA HELD'}",
            f"",
            "## Round-by-Round Results",
            "",
            "| Round | Time | Dev | DevOps | QA | Winner |",
            "|-------|------|-----|--------|----|--------|",
        ]
        for r in rounds:
            lines.append(
                f"| {r.round_num} | {r.timestamp} | {r.dev_verdict} | "
                f"{r.devops_verdict} | {r.qa_verdict} | {r.winner} |"
            )

        lines += ["", "## QA Issues by Round", ""]
        for r in rounds:
            if r.qa_issues:
                lines += [
                    f"### Round {r.round_num} — QA Findings",
                    f"",
                    f"{r.qa_issues}",
                    "",
                ]

        report_path = os.path.join(_PROJECT_ROOT, "output", "confrontation_report.md")
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            print(f"[REPORT] Confrontation report written: {report_path}", flush=True)
        except Exception as e:
            print(f"[REPORT ERROR] {e}", flush=True)


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def kickoff():
    user_idea = "研发一个新的社交媒体应用，目标用户是年轻人，核心功能包括发布动态、好友互动和内容推荐。"
    flow = VirtualRndFlow()
    flow.kickoff(inputs={"user_input": user_idea})


def plot():
    flow = VirtualRndFlow()
    flow.plot("virtual_rnd_flow")


def run_with_trigger():
    user_idea = os.getenv("RND_USER_INPUT", "")
    if not user_idea:
        raise ValueError("RND_USER_INPUT environment variable is required.")
    flow = VirtualRndFlow()
    flow.kickoff(inputs={"user_input": user_idea})


if __name__ == "__main__":
    kickoff()
