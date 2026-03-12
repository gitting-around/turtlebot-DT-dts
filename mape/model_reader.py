from xml.etree import ElementTree as ET
from typing import Any, Dict, List
from metamodel import *

xsi_type = "{http://www.w3.org/2001/XMLSchema-instance}type"

class ModelParser:
    def __init__(self):
        self.objmap: Dict[str, Any] = {}
        self.pending_refs: List[tuple] = []

    def parse(self, xml_string: str) -> ModelRoot:
        root = ET.fromstring(xml_string)
        model = self._parse_node(root, path="/")
        self._resolve_references()
        return model

    # Here we recursively create an object for the node.
    def _parse_node(self, node: ET.Element, path: str) -> Any:
        tag = node.tag.split("}")[-1]
        # Change the path of mission from @mission.0 to @mission
        path = path.replace("@mission.0", "@mission")

        # If the tag is for an abstract class, check xsi:type, otherwise, directly get tag class
        if self._is_tag_abstract_class(tag):
            # Check here the xsi:type, remove the "mddtwin:" prefix and get it
            type = node.attrib.get(xsi_type)
            cls = self._class_for_type(type)
        else:
            cls = self._class_for_tag(tag)
        if not cls:
            print(f"Unknown class for tag: {tag} at path: {path}")
            return None
            # Skip if no class is found
        obj = cls()
        self.objmap[path] = obj

        for k, v in node.attrib.items():
            if k == xsi_type:
                continue
            if self._enum_for_attribute(k) is not None:
                self._assign_enum(obj, k, v)
            elif v.startswith("//@"):
                # Here there is the list of objects that need references to be set
                # Object, property key, reference
                self.pending_refs.append((obj, k, v))
            else:
                setattr(obj, k, v)

        siblings_map = {}
        for child in node:
            ctag = child.tag.split("}")[-1]
            # Count the number of children nodes with the same tag
            sibling_num = siblings_map.get(ctag, -1) + 1
            siblings_map[ctag] = sibling_num
            cpath = f"{path}/@{ctag}.{sibling_num}"
            child_obj = self._parse_node(child, cpath)
            if child_obj is None:
                continue
            self._append_child(obj, ctag, child_obj)
        return obj

    def _class_for_tag(self, tag: str):
        mapping = {
            "ModelRoot": ModelRoot,
            "mission": Mission,
            "task": Task,
            "robot": Robot,
            "source": Source,
            "monitoredrobotproperty": RobotProperty,
            "startObservation": TimeObservation,
            "endObservation": TimeObservation
        }
        return mapping.get(tag)

    def _is_tag_abstract_class(self, tag:str) -> bool:
        abstract_classes_tags = [
            "constraint",
            "bound",
            "value",
            "interestingproperty",
            "environmentproperty"
        ]
        return tag in abstract_classes_tags

    def _class_for_type(self, type:str):
        mapping = {
            "mddtwin:ResourceConstraint": ResourceConstraint,
            "mddtwin:TimeConstraint": TimeConstraint,
            "mddtwin:EnvironmentalConstraint": EnvironmentalConstraint,
            "mddtwin:EnvironmentProperty": EnvironmentProperty,
            "mddtwin:ContextProperty": ContextProperty,
            "mddtwin:SimpleBound": SimpleBound,
            "mddtwin:Interval": Interval,
            "mddtwin:StaticValue": StaticValue,
            "mddtwin:DerivedValue": DerivedValue
        }
        return mapping.get(type)

    def _enum_for_attribute(self, attribute:str):
        mapping = {
            "valueType": ValueType,
            "boundType": BoundType,
            "operand": OperationType,
            "observation": ObservationType,
            "intervalType": IntervalType
        }
        return mapping.get(attribute)

    def _append_child(self, obj, tag, child_obj):
        if hasattr(obj, tag):
            attr = getattr(obj, tag)
            if isinstance(attr, list):
                attr.append(child_obj)
            else:
                setattr(obj, tag, child_obj)
        elif hasattr(obj, tag + "s"):
            getattr(obj, tag + "s").append(child_obj)
        else:
            for f in obj.__dataclass_fields__:
                if isinstance(getattr(obj, f), list) and f.endswith("property"):
                    getattr(obj, f).append(child_obj)
                    return

    def _assign_enum(self, obj, field, value):
        enum_cls = self._enum_for_attribute(field)
        if enum_cls:
            if value in [v.value for v in enum_cls]:
                setattr(obj, field, enum_cls(value))

    def _resolve_references(self):
        for obj, attr, ref in self.pending_refs:
            target = self.objmap.get(ref)
            setattr(obj, attr, target)

def parse_model(xml_string: str) -> ModelRoot:
    return ModelParser().parse(xml_string)

def read_model(model_path: str) -> ModelRoot:
    with open(model_path, 'r') as file:
        xml_string = file.read()
    return parse_model(xml_string)
