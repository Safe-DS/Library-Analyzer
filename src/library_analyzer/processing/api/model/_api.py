from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, TypeAlias

from black import FileMode, InvalidInput, format_str
from black.brackets import BracketMatchError
from black.linegen import CannotSplit
from black.trans import CannotTransform

from library_analyzer.utils import ensure_file_exists, parent_id

from ._docstring import ClassDocstring, FunctionDocstring, ParameterDocstring, ResultDocstring
from ._types import AbstractType, create_type

if TYPE_CHECKING:
    from pathlib import Path

API_SCHEMA_VERSION = 1


class API:
    @staticmethod
    def from_json_file(path: Path) -> API:
        with path.open(encoding="utf-8") as api_file:
            api_json = json.load(api_file)

        return API.from_dict(api_json)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> API:
        result = API(d["distribution"], d["package"], d["version"])

        for module_json in d.get("modules", []):
            result.add_module(Module.from_dict(module_json))

        for class_json in d.get("classes", []):
            result.add_class(Class.from_dict(class_json))

        for function_json in d.get("functions", []):
            result.add_function(Function.from_dict(function_json))

        return result

    def __init__(self, distribution: str, package: str, version: str) -> None:
        self.distribution: str = distribution
        self.package: str = package
        self.version: str = version
        self.modules: dict[str, Module] = {}
        self.classes: dict[str, Class] = {}
        self.functions: dict[str, Function] = {}
        self.attributes_: dict[str, Attribute] | None = None
        self.parameters_: dict[str, Parameter] | None = None
        self.results_: dict[str, Result] | None = None

    def add_module(self, module: Module) -> None:
        self.modules[module.id] = module

    def add_class(self, class_: Class) -> None:
        self.classes[class_.id] = class_

    def add_function(self, function: Function) -> None:
        self.functions[function.id] = function

    def is_public_class(self, class_id: str) -> bool:
        return class_id in self.classes and self.classes[class_id].is_public

    def is_public_function(self, function_id: str) -> bool:
        return function_id in self.functions and self.functions[function_id].is_public

    def class_count(self) -> int:
        return len(self.classes)

    def public_class_count(self) -> int:
        return len([it for it in self.classes.values() if it.is_public])

    def function_count(self) -> int:
        return len(self.functions)

    def public_function_count(self) -> int:
        return len([it for it in self.functions.values() if it.is_public])

    def parameter_count(self) -> int:
        return len(self.parameters())

    def public_parameter_count(self) -> int:
        return len([it for it in self.parameters().values() if it.is_public])

    def parameters(self) -> dict[str, Parameter]:
        if self.parameters_ is not None:
            return self.parameters_
        parameters_: dict[str, Parameter] = {}

        for function in self.functions.values():
            for parameter in function.parameters:
                parameter_id = f"{function.id}/{parameter.name}"
                parameters_[parameter_id] = parameter
        self.parameters_ = parameters_
        return parameters_

    def attributes(self) -> dict[str, Attribute]:
        if self.attributes_ is not None:
            return self.attributes_
        attributes_: dict[str, Attribute] = {}

        for class_ in self.classes.values():
            for attribute in class_.instance_attributes:
                attribute_id = f"{class_.id}/{attribute.name}"
                attributes_[attribute_id] = attribute
        self.attributes_ = attributes_

        return attributes_

    def results(self) -> dict[str, Result]:
        if self.results_ is not None:
            return self.results_
        results_: dict[str, Result] = {}

        for function in self.functions.values():
            for result in function.results:
                result_id = f"{function.id}/{result.name}"
                results_[result_id] = result
        self.results_ = results_
        return results_

    def get_default_value(self, parameter_id: str) -> str | None:
        function_id = parent_id(parameter_id)

        if function_id not in self.functions:
            return None

        for parameter in self.functions[function_id].parameters:
            if parameter.id == parameter_id:
                return parameter.default_value

        return None

    def get_public_api(self) -> API:
        result = API(self.distribution, self.package, self.version)

        for module in self.modules.values():
            result.add_module(module)

        for class_ in self.classes.values():
            if class_.is_public:
                copy = Class(
                    id=class_.id,
                    qname=class_.qname,
                    decorators=class_.decorators,
                    superclasses=class_.superclasses,
                    is_public=class_.is_public,
                    reexported_by=class_.reexported_by,
                    docstring=class_.docstring,
                    code=class_.code,
                    instance_attributes=class_.instance_attributes,
                )
                for method in class_.methods:
                    if self.is_public_function(method):
                        copy.add_method(method)
                result.add_class(copy)

        for function in self.functions.values():
            if function.is_public:
                result.add_function(function)

        return result

    def to_json_file(self, path: Path) -> None:
        ensure_file_exists(path)
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": API_SCHEMA_VERSION,
            "distribution": self.distribution,
            "package": self.package,
            "version": self.version,
            "modules": [module.to_dict() for module in sorted(self.modules.values(), key=lambda it: it.id)],
            "classes": [class_.to_dict() for class_ in sorted(self.classes.values(), key=lambda it: it.id)],
            "functions": [function.to_dict() for function in sorted(self.functions.values(), key=lambda it: it.id)],
        }


class Module:
    @staticmethod
    def from_dict(d: dict[str, Any]) -> Module:
        result = Module(
            d["id"],
            d["name"],
            [Import.from_dict(import_json) for import_json in d.get("imports", [])],
            [FromImport.from_dict(from_import_json) for from_import_json in d.get("from_imports", [])],
        )

        for class_id in d.get("classes", []):
            result.add_class(class_id)

        for function_id in d.get("functions", []):
            result.add_function(function_id)

        return result

    def __init__(self, id_: str, name: str, imports: list[Import], from_imports: list[FromImport]):
        self.id: str = id_
        self.name: str = name
        self.imports: list[Import] = imports
        self.from_imports: list[FromImport] = from_imports
        self.classes: list[str] = []
        self.functions: list[str] = []

    def add_class(self, class_id: str) -> None:
        self.classes.append(class_id)

    def add_function(self, function_id: str) -> None:
        self.functions.append(function_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "imports": [import_.to_dict() for import_ in self.imports],
            "from_imports": [from_import.to_dict() for from_import in self.from_imports],
            "classes": self.classes,
            "functions": self.functions,
        }


@dataclass
class Import:
    module_name: str
    alias: str | None

    @staticmethod
    def from_dict(d: dict[str, Any]) -> Import:
        return Import(d["module"], d["alias"])

    def to_dict(self) -> dict[str, Any]:
        return {"module": self.module_name, "alias": self.alias}


@dataclass
class FromImport:
    module_name: str
    declaration_name: str
    alias: str | None

    @staticmethod
    def from_dict(d: dict[str, Any]) -> FromImport:
        return FromImport(d["module"], d["declaration"], d["alias"])

    def to_dict(self) -> dict[str, Any]:
        return {
            "module": self.module_name,
            "declaration": self.declaration_name,
            "alias": self.alias,
        }


@dataclass
class Class:
    id: str
    qname: str
    decorators: list[str]
    superclasses: list[str]
    methods: list[str] = field(init=False)
    is_public: bool
    reexported_by: list[str]
    docstring: ClassDocstring
    code: str
    instance_attributes: list[Attribute]

    @staticmethod
    def from_dict(d: dict[str, Any]) -> Class:
        result = Class(
            d["id"],
            d["qname"],
            d.get("decorators", []),
            d.get("superclasses", []),
            d.get("is_public", True),
            d.get("reexported_by", []),
            ClassDocstring(description=d.get("description", "")),
            d.get("code", ""),
            [
                Attribute.from_dict(instance_attribute, d["id"])
                for instance_attribute in d.get("instance_attributes", [])
            ],
        )

        for method_id in d["methods"]:
            result.add_method(method_id)

        return result

    def __post_init__(self) -> None:
        self.methods: list[str] = []

    @property
    def name(self) -> str:
        return self.qname.split(".")[-1]

    def add_method(self, method_id: str) -> None:
        self.methods.append(method_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "qname": self.qname,
            "decorators": self.decorators,
            "superclasses": self.superclasses,
            "methods": self.methods,
            "is_public": self.is_public,
            "reexported_by": self.reexported_by,
            "description": self.docstring.description,
            "code": self.code,
            "instance_attributes": [attribute.to_dict() for attribute in self.instance_attributes],
        }

    def get_formatted_code(self, *, cut_documentation: bool = False) -> str:
        formatted_code = _generate_formatted_code(self)
        if cut_documentation:
            formatted_code = _cut_documentation_from_code(formatted_code, self)
        return formatted_code


def _generate_formatted_code(api_element: Class | Function) -> str:
    code = api_element.code
    try:
        code_tmp = format_str(code, mode=FileMode())
    except (CannotSplit, CannotTransform, InvalidInput, BracketMatchError):
        # As long as the api black has no documentation, we do not know which exceptions are raised
        pass
    else:
        code = code_tmp
    return code


def _cut_documentation_from_code(code: str, api_element: Class | Function) -> str:
    start_keyword = "class " if isinstance(api_element, Class) else "def "
    lines = code.split("\n")
    start_line = -1
    for index, line in enumerate(lines):
        if line.lstrip().startswith(start_keyword):
            start_line = index + 1
            break
    if 0 <= start_line < len(lines):
        line = lines[start_line].lstrip()
        if line.startswith('"""'):
            end_line = -1
            lines[start_line] = line[3:]
            if lines[start_line].rstrip().endswith('"""'):
                end_line = start_line
            else:
                for index in range(start_line, len(lines)):
                    line = lines[index]
                    if line.lstrip().startswith('"""'):
                        end_line = index
                        break
            if end_line >= 0:
                if (end_line + 1) < len(lines) and lines[end_line + 1].lstrip() == "":
                    end_line += 1
                return "\n".join(lines[:start_line]) + "\n" + "\n".join(lines[end_line + 1 :])
    return code


@dataclass(frozen=True)
class Attribute:
    id: str
    name: str
    types: AbstractType | None
    class_id: str | None = None

    @staticmethod
    def from_dict(d: dict[str, Any], class_id: str | None = None) -> Attribute:
        return Attribute(d["id"], d["name"], AbstractType.from_dict(d.get("types", {})), class_id)

    def to_dict(self) -> dict[str, Any]:
        types_json = self.types.to_dict() if self.types is not None else None
        return {"id": self.id, "name": self.name, "types": types_json}


@dataclass(frozen=True)
class Function:
    id: str
    qname: str
    decorators: list[str]
    parameters: list[Parameter]
    results: list[Result]
    is_public: bool
    reexported_by: list[str]
    docstring: FunctionDocstring
    code: str

    @staticmethod
    def from_dict(d: dict[str, Any]) -> Function:
        return Function(
            d["id"],
            d["qname"],
            d.get("decorators", []),
            [Parameter.from_dict(parameter_json) for parameter_json in d.get("parameters", [])],
            [Result.from_dict(result_json) for result_json in d.get("results", [])],
            d.get("is_public", True),
            d.get("reexported_by", []),
            FunctionDocstring(description=d.get("description", "")),
            d.get("code", ""),
        )

    @property
    def name(self) -> str:
        return self.qname.rsplit(".", maxsplit=1)[-1]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "qname": self.qname,
            "decorators": self.decorators,
            "parameters": [parameter.to_dict() for parameter in self.parameters],
            "results": [result.to_dict() for result in self.results],
            "is_public": self.is_public,
            "reexported_by": self.reexported_by,
            "description": self.docstring.description,
            "code": self.code,
        }

    def get_formatted_code(self, *, cut_documentation: bool = False) -> str:
        formatted_code = _generate_formatted_code(self)
        if cut_documentation:
            formatted_code = _cut_documentation_from_code(formatted_code, self)
        return formatted_code


class Parameter:
    @staticmethod
    def from_dict(d: dict[str, Any]) -> Parameter:
        return Parameter(
            d["id"],
            d["name"],
            d["qname"],
            d.get("default_value", None),
            ParameterAssignment[d.get("assigned_by", "POSITION_OR_NAME")],
            d.get("is_public", True),
            ParameterDocstring.from_dict(d.get("docstring", {})),
        )

    def __hash__(self) -> int:
        return hash(
            (
                self.id,
                self.name,
                self.qname,
                self.default_value,
                self.assigned_by,
                self.is_public,
                self.docstring,
            ),
        )

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Parameter)
            and self.id == other.id
            and self.name == other.name
            and self.qname == other.qname
            and self.default_value == other.default_value
            and self.assigned_by == other.assigned_by
            and self.is_public == other.is_public
            and self.docstring == other.docstring
            and self.type == other.type
        )

    def __init__(
        self,
        id_: str,
        name: str,
        qname: str,
        default_value: str | None,
        assigned_by: ParameterAssignment,
        is_public: bool,
        docstring: ParameterDocstring,
    ) -> None:
        self.id: str = id_
        self.name: str = name
        self.qname: str = qname
        self.default_value: str | None = default_value
        self.assigned_by: ParameterAssignment = assigned_by
        self.is_public: bool = is_public
        self.docstring = docstring
        self.type: AbstractType | None = create_type(docstring.type, docstring.description)

    def is_optional(self) -> bool:
        return self.default_value is not None

    def is_required(self) -> bool:
        return self.default_value is None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "qname": self.qname,
            "default_value": self.default_value,
            "assigned_by": self.assigned_by.name,
            "is_public": self.is_public,
            "docstring": self.docstring.to_dict(),
            "type": self.type.to_dict() if self.type is not None else {},
        }


class AttributeAssignment(Enum):
    """
    How arguments are assigned to attributes. The attributes must appear exactly in this order in an attribute list.

    IMPLICIT attributes appear on instance methods (usually called "self") and on class methods (usually called "cls").
    POSITION_ONLY attributes precede the "/" in an attribute list. NAME_ONLY attributes follow the "*" or the
    POSITIONAL_VARARGS attribute ("*args"). Between the "/" and the "*" the POSITION_OR_NAME attributes reside. Finally,
    the attribute list might optionally include a NAMED_VARARG attribute ("**kwargs").
    """

    IMPLICIT = "IMPLICIT"
    POSITION_ONLY = "POSITION_ONLY"
    POSITION_OR_NAME = "POSITION_OR_NAME"
    POSITIONAL_VARARG = "POSITIONAL_VARARG"
    NAME_ONLY = "NAME_ONLY"
    NAMED_VARARG = "NAMED_VARARG"


class ParameterAssignment(Enum):
    """
    How arguments are assigned to parameters. The parameters must appear exactly in this order in a parameter list.

    IMPLICIT parameters appear on instance methods (usually called "self") and on class methods (usually called "cls").
    POSITION_ONLY parameters precede the "/" in a parameter list. NAME_ONLY parameters follow the "*" or the
    POSITIONAL_VARARGS parameter ("*args"). Between the "/" and the "*" the POSITION_OR_NAME parameters reside. Finally,
    the parameter list might optionally include a NAMED_VARARG parameter ("**kwargs").
    """

    IMPLICIT = "IMPLICIT"
    POSITION_ONLY = "POSITION_ONLY"
    POSITION_OR_NAME = "POSITION_OR_NAME"
    POSITIONAL_VARARG = "POSITIONAL_VARARG"
    NAME_ONLY = "NAME_ONLY"
    NAMED_VARARG = "NAMED_VARARG"


@dataclass(frozen=True)
class Result:
    id: str
    name: str
    docstring: ResultDocstring
    function_id: str | None = None

    @staticmethod
    def from_dict(d: dict[str, Any], function_id: str | None = None) -> Result:
        return Result(
            d["id"],
            d["name"],
            ResultDocstring.from_dict(d.get("docstring", {})),
            function_id,
        )

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "docstring": self.docstring.to_dict()}


ApiElement: TypeAlias = Module | Class | Attribute | Function | Parameter | Result
