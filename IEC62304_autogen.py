#!/usr/bin/env python3
"""IEC 62304 Compliance Auditor - Multi-agent system for medical software lifecycle audit"""

import asyncio
import glob
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from dotenv import load_dotenv

from autogen_agentchat.agents import AssistantAgent, SocietyOfMindAgent
from autogen_agentchat.conditions import (
    MaxMessageTermination, TextMentionTermination,
    TimeoutTermination, TokenUsageTermination
)
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_core.models import ModelFamily, ModelInfo
from autogen_ext.models.anthropic import AnthropicChatCompletionClient

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None
try:
    import docx
except ImportError:
    docx = None
try:
    import openpyxl
except ImportError:
    openpyxl = None


class TokenAccumulator:
    """Track Claude API token usage for cost management"""
    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0

    def add_usage(self, usage: Optional[Dict[str, Any]]):
        if not usage:
            return
        self.input_tokens += usage.get("prompt_tokens", 0) + usage.get("input_tokens", 0)
        self.output_tokens += usage.get("completion_tokens", 0) + usage.get("output_tokens", 0)

    def report(self) -> str:
        total = self.input_tokens + self.output_tokens
        return f"Tokens - Total: {total}, In: {self.input_tokens}, Out: {self.output_tokens}"


# IEC 62304 Audit Schema - maps to regulatory requirements
AUDIT_SCHEMA = {
    "standard": "IEC 62304:2006+A1:2015",
    "software_safety_class": "A|B|C",  # Per IEC 62304:4.3
    "summary": "<=120 words",
    "overall_risk_statement": "paragraph",
    "findings": [{
        "clause": "5.x.x",  # IEC 62304 clause reference
        "area": "Development planning|Requirements|Architecture|Unit impl|"
                "Integration|Verification|Risk mgmt|Config mgmt|Problem resolution|SOUP",
        "requirement": "short",
        "evidence_seen": ["..."],
        "status": "CONFORMING|MINOR_NC|MAJOR_NC|OBSERVATION",
        "severity": "LOW|MEDIUM|HIGH",  # Per ISO 14971 risk levels
        "gap": "if any",
        "impact": "safety/quality/regulatory",
        "recommendation": "actionable",
        "priority": "P1|P2|P3",
        "owner": "role/team",
        "due_date": "YYYY-MM-DD"
    }],
    "nonconformity_register": [{
        "id": "NC-###",
        "clause": "x.x.x",
        "title": "short",
        "category": "MINOR|MAJOR",  # Per ISO 13485 audit categories
        "root_cause_hypothesis": "",
        "containment": "",
        "correction": "",
        "corrective_action": "",
        "verification_of_effectiveness": "",
        "target_close_date": "YYYY-MM-DD"
    }],
    "appendix": {"assumptions": ["..."], "open_questions": ["..."]},
    "signal": "AUDIT_COMPLETE"
}

# Agent system prompts - aligned to IEC 62304 roles
PROMPTS = {
    "lead": f"Lead IEC 62304 Auditor: Ensure lifecycle coverage, set Safety Class, "
            f"compile ONE JSON per schema, end with AUDIT_COMPLETE. Schema: {json.dumps(AUDIT_SCHEMA, separators=(',', ':'))}",
    
    "classifier": "Safety Classification Auditor: Determine A/B/C per IEC 62304:4.3 "
                  "(A=no injury/damage, B=non-serious injury, C=death/serious injury). "
                  "List missing hazard analysis if unclear.",
    
    "lifecycle": "Lifecycle Auditor (§5.1-5.7): Verify planning, requirements, architecture, "
                 "detailed design, unit/integration/system testing per Safety Class.",
    
    "rcp": "Risk/Config/Problem Auditor: Verify ISO 14971 integration (§4), "
           "configuration management (§5.8), problem resolution (§9).",
    
    "soup": "SOUP Auditor (§8): Check identification, evaluation criteria, "
            "known anomalies, change monitoring. Flag undeclared dependencies.",
    
    "trace": "Traceability Auditor: Verify bi-directional links per IEC 62304:5.1.1 "
             "(Requirements↔Design↔Code↔Tests↔Risks), coverage for Class B/C.",
    
    "translator": "แปลเฉพาะ summary และ nonconformity_register เป็นภาษาไทยแบบเป็นทางการ "
                  "คง JSON structure เดิม"
}


@dataclass
class EvidenceItem:
    path: Path
    kind: str
    title: str
    excerpt: str


def build_model_client() -> AnthropicChatCompletionClient:
    """Initialize Claude with IEC 62304 audit parameters"""
    return AnthropicChatCompletionClient(
        model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
        api_key=os.environ["ANTHROPIC_API_KEY"]
    )


def build_team() -> RoundRobinGroupChat:
    """Assemble IEC 62304 audit team per regulatory roles"""
    client = build_model_client()
    
    # Create specialized auditors per IEC 62304 domains
    agents = {
        name: AssistantAgent(name=f"{name}_auditor", model_client=client, system_message=prompt)
        for name, prompt in PROMPTS.items() if name != "translator"
    }
    
    # Phase 1: Technical audit per IEC 62304
    phase1_termination = (
        TextMentionTermination(text="AUDIT_COMPLETE") |
        MaxMessageTermination(max_messages=16) |
        TimeoutTermination(timeout_seconds=90)
    )
    
    phase1 = RoundRobinGroupChat(
        participants=[agents[k] for k in ["classifier", "lifecycle", "rcp", "soup", "trace", "lead"]],
        termination_condition=phase1_termination
    )
    
    som = SocietyOfMindAgent(
        name="society_of_mind_auditor",
        team=phase1,
        model_client=client
    )
    
    # Phase 2: Translation for regulatory submission
    translator = AssistantAgent(
        name="translator_th",
        model_client=client,
        system_message=PROMPTS["translator"]
    )
    
    return RoundRobinGroupChat(participants=[som, translator], max_turns=2)


def discover_paths(patterns: Sequence[str]) -> List[Path]:
    """Expand patterns to unique file paths"""
    paths = []
    for pat in patterns:
        for p in glob.glob(pat):
            path = Path(p).expanduser().resolve()
            if path.exists() and path.is_file():
                paths.append(path)
    return list(dict.fromkeys(paths))  # Dedupe preserving order


def read_pdf(path: Path, max_chars: int = 2000) -> str:
    """Extract technical documentation from PDF"""
    if not PdfReader:
        return "(Install pypdf)"
    try:
        reader = PdfReader(str(path))
        texts = []
        for i, page in enumerate(reader.pages[:10]):
            if txt := (page.extract_text() or "").strip():
                texts.append(f"[p{i+1}] {txt}")
                if sum(len(t) for t in texts) > max_chars:
                    break
        return clean_text("\n".join(texts))[:max_chars]
    except Exception as e:
        return f"(PDF error: {e})"


def read_docx(path: Path, max_chars: int = 2000) -> str:
    """Extract specifications from DOCX"""
    if not docx:
        return "(Install python-docx)"
    try:
        d = docx.Document(str(path))
        paras = [p.text.strip() for p in d.paragraphs if p.text.strip()]
        return clean_text("\n".join(paras))[:max_chars]
    except Exception as e:
        return f"(DOCX error: {e})"


def read_xlsx(path: Path, max_chars: int = 2000) -> str:
    """Extract test matrices/traceability from XLSX"""
    if not openpyxl:
        return "(Install openpyxl)"
    try:
        wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
        parts = []
        for ws in wb.worksheets[:3]:
            rows = []
            for row in ws.iter_rows(min_row=1, max_row=20):
                vals = [str(cell.value) if cell.value else "" for cell in row]
                rows.append(", ".join(vals))
                if sum(len(r) for r in rows) > max_chars // 2:
                    break
            if rows:
                parts.append(f"[{ws.title}] " + " | ".join(rows))
                if sum(len(p) for p in parts) > max_chars:
                    break
        return clean_text("\n".join(parts))[:max_chars]
    except Exception as e:
        return f"(XLSX error: {e})"


def clean_text(text: str) -> str:
    """Minimize tokens while preserving meaning"""
    return re.sub(r"\r?\n+", "\n", re.sub(r"[ \t]+", " ", text)).strip()


def load_evidence(paths: Sequence[Path], per_file: int = 1600) -> List[EvidenceItem]:
    """Extract IEC 62304 evidence from documentation"""
    items = []
    handlers = {".pdf": (read_pdf, "pdf"), ".docx": (read_docx, "docx"), 
                ".xlsx": (read_xlsx, "xlsx")}
    
    for p in paths:
        if (ext := p.suffix.lower()) in handlers:
            reader, kind = handlers[ext]
            items.append(EvidenceItem(
                path=p, kind=kind, title=p.name,
                excerpt=reader(p, max_chars=per_file)
            ))
    return items


def build_context(items: Sequence[EvidenceItem], max_chars: int = 10000) -> Tuple[str, List[str]]:
    """Build token-efficient audit context"""
    lines = ["Evidence:"]
    filenames = []
    remaining = max_chars - len(lines[0])
    
    for it in items:
        if remaining <= 0:
            break
        chunk = f"\n## {it.title} ({it.kind})\n{it.excerpt}\n"
        if len(chunk) > remaining:
            chunk = chunk[:remaining]
        lines.append(chunk)
        filenames.append(it.title)
        remaining -= len(chunk)
    
    return "".join(lines), filenames


async def run_audit(team: RoundRobinGroupChat, items: List[EvidenceItem]):
    """Execute IEC 62304 compliance audit"""
    if not items:
        print("No evidence. Use `add <files>`")
        return
    
    context, filenames = build_context(items)
    print(f"Context length: {len(context)} chars")
    
    # IEC 62304 audit task per regulatory requirements
    task = (
        "IEC 62304 Compliance Audit:\n"
        "1. Classify software per IEC 62304:4.3 (A/B/C)\n"
        "2. Verify lifecycle processes (§5.1-5.8)\n"
        "3. Check SOUP management (§8)\n"
        "4. Validate risk management per ISO 14971\n"
        "5. Output ONE JSON per schema\n"
        "6. End with AUDIT_COMPLETE\n\n"
        f"{context}\n"
        f"Files: {filenames}"
    )
    
    print("Starting audit...")
    result = await team.run(task=task)
    
    print("\n=== IEC 62304 Audit Results ===")
    total_input = sum(getattr(msg, 'usage', {}).get('input_tokens', 0) for msg in result.messages if hasattr(msg, 'usage'))
    total_output = sum(getattr(msg, 'usage', {}).get('output_tokens', 0) for msg in result.messages if hasattr(msg, 'usage'))
    print(f"Tokens - Total: {total_input + total_output}, In: {total_input}, Out: {total_output}")
    
    for msg in result.messages:
        print(f"[{msg.source}]: {msg.content}")
        print("-" * 50)


async def main():
    """IEC 62304 Audit CLI"""
    team = build_team()
    
    queue = []
    print("\nIEC 62304 Auditor Commands:")
    print("  add <files>  - Add documentation")
    print("  list        - Show queued files")
    print("  clear       - Clear queue")
    print("  run         - Execute audit")
    print("  quit        - Exit\n")
    
    while True:
        try:
            if not (raw := input("iec62304> ").strip()):
                continue
            cmd, *args = raw.split()
            cmd = cmd.lower()
            
            if cmd in {"quit", "exit"}:
                break
            
            if cmd == "add":
                if not args:
                    print("Usage: add <files>")
                    continue
                found = [p for p in discover_paths(args) 
                        if p.suffix.lower() in {".pdf", ".docx", ".xlsx"}]
                if found:
                    queue.extend([p for p in found if p not in queue])
                    print(f"Added {len(found)} files")
                else:
                    print("No supported files found")
            
            elif cmd == "list":
                if queue:
                    for i, p in enumerate(queue, 1):
                        print(f"{i:2d}. {p}")
                else:
                    print("Queue empty")
            
            elif cmd == "clear":
                queue.clear()
                print("Queue cleared")
            
            elif cmd == "run":
                if queue:
                    await run_audit(team, load_evidence(queue))
                else:
                    print("Queue empty")
            
            else:
                print("Unknown command")
                
        except (EOFError, KeyboardInterrupt):
            break
    
    print("\nBye.")


if __name__ == "__main__":
    load_dotenv()
    if "ANTHROPIC_API_KEY" not in os.environ:
        print("ERROR: Set ANTHROPIC_API_KEY")
        exit(1)
    asyncio.run(main())