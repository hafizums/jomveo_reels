from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Finding:
    severity: str
    category: str
    file: str
    line: int
    message: str
    suggestion: str
    evidence: str

    def to_dict(self):
        return asdict(self)
