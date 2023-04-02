from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from black import FileMode, InvalidInput, format_str
from black.brackets import BracketMatchError
from black.linegen import CannotSplit
from black.trans import CannotTransform

from library_analyzer.utils import parent_id

from ._documentation import ClassDocumentation, FunctionDocumentation
from ._parameters import Parameter
from ._types import AbstractType

API_SCHEMA_VERSION = 1


class API:
    @staticmethod
    def from_json(json: Any) -> API:
        result = API(json["distribution"], json["package"], json["version"])

        for module_json in json.get("modules", []):
            result.add_module(Module.from_json(module_json))

        for class_json in json.get("classes", []):
            result.add_class(Class.from_json(class_json))

        for function_json in json.get("functions", []):
            result.add_function(Function.from_json(function_json))

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

    def to_json(self) -> Any:
        return {
            "schemaVersion": API_SCHEMA_VERSION,
            "distribution": self.distribution,
            "package": self.package,
            "version": self.version,
            "modules": [module.to_json() for module in sorted(self.modules.values(), key=lambda it: it.id)],
            "classes": [class_.to_json() for class_ in sorted(self.classes.values(), key=lambda it: it.id)],
            "functions": [function.to_json() for function in sorted(self.functions.values(), key=lambda it: it.id)],
        }


class Module:
    @staticmethod
    def from_json(json: Any) -> Module:
        result = Module(
            json["id"],
            json["name"],
            [Import.from_json(import_json) for import_json in json.get("imports", [])],
            [FromImport.from_json(from_import_json) for from_import_json in json.get("from_imports", [])],
        )

        for class_id in json.get("classes", []):
            result.add_class(class_id)

        for function_id in json.get("functions", []):
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

    def to_json(self) -> Any:
        return {
            "id": self.id,
            "name": self.name,
            "imports": [import_.to_json() for import_ in self.imports],
            "from_imports": [from_import.to_json() for from_import in self.from_imports],
            "classes": self.classes,
            "functions": self.functions,
        }


@dataclass
class Import:
    module_name: str
    alias: str | None

    @staticmethod
    def from_json(json: Any) -> Import:
        return Import(json["module"], json["alias"])

    def to_json(self) -> Any:
        return {"module": self.module_name, "alias": self.alias}


@dataclass
class FromImport:
    module_name: str
    declaration_name: str
    alias: str | None

    @staticmethod
    def from_json(json: Any) -> FromImport:
        return FromImport(json["module"], json["declaration"], json["alias"])

    def to_json(self) -> Any:
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
    documentation: ClassDocumentation
    code: str
    instance_attributes: list[Attribute]

    @staticmethod
    def from_json(json: Any) -> Class:
        result = Class(
            json["id"],
            json["qname"],
            json.get("decorators", []),
            json.get("superclasses", []),
            json.get("is_public", True),
            json.get("reexported_by", []),
            ClassDocumentation(
                description=json.get("description", ""),
                full_docstring=json.get("docstring", ""),
            ),
            json.get("code", ""),
            [
                Attribute.from_json(instance_attribute, json["id"])
                for instance_attribute in json.get("instance_attributes", [])
            ],
        )

        for method_id in json["methods"]:
            result.add_method(method_id)

        return result

    def __post_init__(self) -> None:
        self.methods: list[str] = []

    @property
    def name(self) -> str:
        return self.qname.split(".")[-1]

    def add_method(self, method_id: str) -> None:
        self.methods.append(method_id)

    def to_json(self) -> Any:
        return {
            "id": self.id,
            "name": self.name,
            "qname": self.qname,
            "decorators": self.decorators,
            "superclasses": self.superclasses,
            "methods": self.methods,
            "is_public": self.is_public,
            "reexported_by": self.reexported_by,
            "description": self.documentation.description,
            "docstring": self.documentation.full_docstring,
            "code": self.code,
            "instance_attributes": [attribute.to_json() for attribute in self.instance_attributes],
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
    name: str
    types: AbstractType | None
    class_id: str | None = None

    def to_json(self) -> dict[str, Any]:
        types_json = self.types.to_json() if self.types is not None else None
        return {"name": self.name, "types": types_json}

    @staticmethod
    def from_json(json: Any, class_id: str | None = None) -> Attribute:
        return Attribute(json["name"], AbstractType.from_json(json.get("types", {})), class_id)


@dataclass(frozen=True)
class Function:
    id: str
    qname: str
    decorators: list[str]
    parameters: list[Parameter]
    results: list[Result]
    is_public: bool
    reexported_by: list[str]
    documentation: FunctionDocumentation
    code: str

    @staticmethod
    def from_json(json: Any) -> Function:
        return Function(
            json["id"],
            json["qname"],
            json.get("decorators", []),
            [Parameter.from_json(parameter_json) for parameter_json in json.get("parameters", [])],
            [Result.from_json(result_json) for result_json in json.get("results", [])],
            json.get("is_public", True),
            json.get("reexported_by", []),
            FunctionDocumentation(
                description=json.get("description", ""),
                full_docstring=json.get("docstring", ""),
            ),
            json.get("code", ""),
        )

    @property
    def name(self) -> str:
        return self.qname.rsplit(".", maxsplit=1)[-1]

    def to_json(self) -> Any:
        return {
            "id": self.id,
            "name": self.name,
            "qname": self.qname,
            "decorators": self.decorators,
            "parameters": [parameter.to_json() for parameter in self.parameters],
            "results": [result.to_json() for result in self.results],
            "is_public": self.is_public,
            "reexported_by": self.reexported_by,
            "description": self.documentation.description,
            "docstring": self.documentation.full_docstring,
            "code": self.code,
        }

    def get_formatted_code(self, *, cut_documentation: bool = False) -> str:
        formatted_code = _generate_formatted_code(self)
        if cut_documentation:
            formatted_code = _cut_documentation_from_code(formatted_code, self)
        return formatted_code


@dataclass(frozen=True)
class Result:
    name: str
    docstring: ResultDocstring
    function_id: str | None = None

    @staticmethod
    def from_json(json: Any, function_id: str | None = None) -> Result:
        return Result(
            json["name"],
            ResultDocstring.from_json(json.get("docstring", {})),
            function_id,
        )

    def to_json(self) -> Any:
        return {"name": self.name, "docstring": self.docstring.to_json()}


@dataclass(frozen=True)
class ResultDocstring:
    type: str
    description: str

    @staticmethod
    def from_json(json: Any) -> ResultDocstring:
        return ResultDocstring(
            json.get("type", ""),
            json.get("description", ""),
        )

    def to_json(self) -> Any:
        return {"type": self.type, "description": self.description}
