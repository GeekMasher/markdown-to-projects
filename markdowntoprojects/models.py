from typing import List
from dataclasses import dataclass, field


def loader(klass, dikt):
    try:
        fieldtypes = klass.__annotations__
        return klass(**{f: loader(fieldtypes[f], dikt[f]) for f in dikt})

    except KeyError as err:
        raise Exception(f"Unknown key being set in configuration file : {err}")

    except AttributeError as err:
        if isinstance(dikt, (tuple, list)):
            return [loader(klass.__args__[0], f) for f in dikt]
        return dikt


@dataclass
class ConfigIssues:
    name: str
    content: str
    labels: List[str] = field(default_factory=list)
    # ID from API response
    id: int = None


@dataclass
class ConfigProject:
    name: str
    description: str = ""
    columns: List[str] = field(default_factory=list)


@dataclass
class Config:
    project: ConfigProject
    root: str = "."
    default_column: str = "Backlog"
    issues: List[ConfigIssues] = field(default_factory=list)
