from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
from enum import Enum
from abc import ABC

class ValueType(Enum):
    INT = "int"
    STRING = "string"
    BOOLEAN = "boolean"
    FLOAT = "float"

class BoundType(Enum):
    AT_MOST = "at_most"
    GREATER_THAN = "greater_than"
    AT_LEAST = "at_least"
    EXACTLY = "exactly"
    LESS_THAN = "less_than"

class IntervalType(Enum):
    WITHIN = "within"
    STRICTLY_WITHIN = "strictly_within"

class ObservationType(Enum):
    START = "start"
    END = "end"

class OperationType(Enum):
    PRODUCT = "product"
    SUM = "sum"
    DIFFERENCE = "difference"
    RATIO = "ratio"
    NONE = "none"

class ConstraintLevel(Enum):
    SOFT = "soft"
    HARD = "hard"

@dataclass
class Source:
    topic: str = None
    datapath: str = None

@dataclass
class Value(ABC):
    pass

@dataclass
class StaticValue(Value):
    valueType: ValueType = ValueType.STRING
    valueLiteral: str = None

@dataclass
class DerivedValue(Value):
    baseProperty: List[MeasuredProperty] = field(default_factory=list)
    operand: OperationType = OperationType.NONE

@dataclass
class Bound(ABC):
    pass

@dataclass
class SimpleBound(Bound):
    boundType: BoundType = BoundType.AT_MOST
    value: Value = None

@dataclass
class Interval(Bound):
    intervalType: IntervalType = IntervalType.WITHIN
    value: List[Value] = field(default_factory=list)

@dataclass
class MeasuredProperty(ABC):
    source: Source = None
    name: str = None
    valueType: ValueType = ValueType.STRING

@dataclass
class RobotProperty(MeasuredProperty):
    pass

@dataclass
class EnvironmentProperty(MeasuredProperty):
    pass

@dataclass
class ContextProperty(MeasuredProperty):
    pass

@dataclass
class Constraint(ABC):
    name: str = None
    bound: List[Bound] = field(default_factory=list)

@dataclass
class ResourceConstraint(Constraint):
    monitoredrobotproperty: RobotProperty = None

@dataclass
class TimeConstraint(Constraint):
    startObservation: TimeObservation = None
    endObservation: TimeObservation = None

@dataclass
class EnvironmentalConstraint(Constraint):
    environmentproperty: EnvironmentProperty = None

@dataclass
class TimeObservation:
    task: Task = None
    observation: ObservationType = ObservationType.START

@dataclass
class Task:
    name: str = None
    dependsOn: Task = None
    constraint: List[Constraint] = field(default_factory=list)

@dataclass
class Robot:
    name: str = None
    monitoredrobotproperty: List[RobotProperty] = field(default_factory=list)

@dataclass
class Mission:
    task: List[Task] = field(default_factory=list)
    name: str = None
    robot: Robot = None
    interestingproperty: List[MeasuredProperty] = field(default_factory=list)
    constraint: List[Constraint] = field(default_factory=list)

@dataclass
class ModelRoot:
    mission: Mission = None
    constraint: List[Constraint] = field(default_factory=list)
    environmentproperty: List[EnvironmentProperty] = field(default_factory=list)
    robot: List[Robot] = field(default_factory=list)