from dataclasses import dataclass, field
from .certification_result import CertificationResult

@dataclass(slots=True)
class CertificationReport:
    """Aggregates every certification validator."""

    phase: str
    engine_version: str
    results: list[CertificationResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(result.passed for result in self.results)

    def add(self, result: CertificationResult) -> None:
        self.results.append(result)

    def to_markdown(self) -> str:
        lines=[f"# Phase {self.phase} Certification Report","",f"**Overall status:** {'PASS' if self.passed else 'FAIL'}",f"**Engine version:** {self.engine_version}","","| Gate | Status | Duration | Message |","|---|---:|---:|---|"]
        for result in self.results:
            lines.append(f"| {result.validator_name} | {'PASS' if result.passed else 'FAIL'} | {result.duration_seconds:.4f}s | {result.message} |")
        lines.extend(["","## Metadata",""])
        for result in self.results: lines.append(f"- **{result.validator_name}:** `{dict(result.metadata)}`")
        return "\n".join(lines)+"\n"
