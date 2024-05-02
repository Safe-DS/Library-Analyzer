import json
from pathlib import Path

import astroid
from library_analyzer.cli._run_api import _run_api_command
from library_analyzer.processing.api.docstring_parsing import DocstringStyle
from library_analyzer.processing.api.purity_analysis import get_purity_results
from library_analyzer.processing.api.purity_analysis.model import (
    ClassScope,
    ClassVariable,
    GlobalVariable,
    LocalVariable,
    NodeID,
    Symbol,
)
from library_analyzer.utils import ASTWalker


def test_run_api_command_safe_ds() -> None:
    _run_api_command("safe-ds",
                     Path(r"C:\Users\Lukas Radermacher\AppData\Local\pypoetry\Cache\virtualenvs\library-analyzer-FK1WveJV-py3.11\Lib\site-packages\safeds"),
                     Path(r"D:\Ergebnisse BA\Results\SafeDS"),
                     DocstringStyle.NUMPY,
                     )

def test_run_api_command_pandas() -> None:
    _run_api_command("pandas",
                     Path(r"D:\Ergebnisse BA\Results\Pandas\pandas_v2.0.3"),
                     Path(r"D:\Ergebnisse BA\Results\Pandas"),
                     DocstringStyle.NUMPY,
                     )

def test_run_api_command_scikit() -> None:
    _run_api_command("scikit",
                     Path(r"D:\Ergebnisse BA\Results\SciKit\sklearn_v1.3.0"),
                     Path(r"D:\Ergebnisse BA\Results\SciKit"),
                     DocstringStyle.NUMPY,
                     )


def test_run_api_command_pytorch() -> None:
    _run_api_command("pytorch",
                     Path(r"D:\Ergebnisse BA\Results\Pytorch\pytorch_v2.0.1"),
                     Path(r"D:\Ergebnisse BA\Results\Pytorch"),
                     DocstringStyle.NUMPY,
                     )

def test_run_api_command_seaborn() -> None:
    _run_api_command("seaborn",
                     Path(r"D:\Ergebnisse BA\Results\Seaborn\seaborn_v0.12.2"),
                     Path(r"D:\Ergebnisse BA\Results\Seaborn"),
                     DocstringStyle.NUMPY,
                     )

def test_run_api_command_small_module() -> None:
    _run_api_command("tracemalloce",
                     Path(r"D:\Ergebnisse BA\Results"),
                     Path(r"D:\Ergebnisse BA\Results"),
                     DocstringStyle.NUMPY,
                     )


def test_single_ds_file() -> None:
    res = get_purity_results(Path(r"C:\Users\Lukas Radermacher\AppData\Local\pypoetry\Cache\virtualenvs\library-analyzer-FK1WveJV-py3.11\Lib\site-packages\safeds\data\tabular\containers"))
    out_file_api_purity = Path(r"D:\Ergebnisse BA\Results\Tests").joinpath("single_api_purity.json")
    res.to_json_file(out_file_api_purity)

class_dict = {
    "ArithmeticError": "",
    "AssertionError": "",
    "AttributeError": "",
    "BaseException": "",
    "BaseExceptionGroup": "",
    "BlockingIOError": "",
    "BrokenPipeError": "",
    "BufferError": "",
    "BytesWarning": "",
    "ChildProcessError": "",
    "ConnectionAbortedError": "",
    "ConnectionError": "",
    "ConnectionRefusedError": "",
    "ConnectionResetError": "",
    "DeprecationWarning": "",
    "EOFError": "",
    "Ellipsis": "",
    "EncodingWarning": "",
    "EnvironmentError": "",
    "Exception": "",
    "ExceptionGroup": "",
    "False": "",
    "FileExistsError": "",
    "FileNotFoundError": "",
    "FloatingPointError": "",
    "FutureWarning": "",
    "GeneratorExit": "",
    "IOError": "",
    "ImportError": "",
    "ImportWarning": "",
    "IndentationError": "",
    "IndexError": "",
    "InterruptedError": "",
    "IsADirectoryError": "",
    "KeyError": "",
    "KeyboardInterrupt": "",
    "LookupError": "",
    "MemoryError": "",
    "ModuleNotFoundError": "",
    "NameError": "",
    "None": "",
    "NotADirectoryError": "",
    "NotImplemented": "",
    "NotImplementedError": "",
    "OSError": "",
    "OverflowError": "",
    "PendingDeprecationWarning": "",
    "PermissionError": "",
    "ProcessLookupError": "",
    "RecursionError": "",
    "ReferenceError": "",
    "ResourceWarning": "",
    "RuntimeError": "",
    "RuntimeWarning": "",
    "StopAsyncIteration": "",
    "StopIteration": "",
    "SyntaxError": "",
    "SyntaxWarning": "",
    "SystemError": "",
    "SystemExit": "",
    "TabError": "",
    "TimeoutError": "",
    "True": "",
    "TypeError": "",
    "UnboundLocalError": "",
    "UnicodeDecodeError": "",
    "UnicodeEncodeError": "",
    "UnicodeError": "",
    "UnicodeTranslateError": "",
    "UnicodeWarning": "",
    "UserWarning": "",
    "ValueError": "",
    "Warning": "",
    "WindowsError": "",
    "ZeroDivisionError": "",
}


def test_build_class_scopes() -> dict[str, ClassScope]:
    global class_dict
    class ScopesBuilder:
        def __init__(self) -> None:
            self.scopes: dict[str, ClassScope] = {}
            self.current_class: str | None = None

        def enter_classdef(self, node: astroid.ClassDef) -> None:
            symbol = GlobalVariable(node=node, id=NodeID("BUILTIN", node.name, node.lineno, node.col_offset), name=node.name)
            self.scopes[node.name] = ClassScope(symbol, [], None, {})
            self.current_class = node.name

        def leave_classdef(self, node: astroid.ClassDef) -> None:
            self.current_class = None

        def enter_functiondef(self, node: astroid.FunctionDef) -> None:
            if not self.current_class:
                return
            symbol = ClassVariable(node=node,
                                   id=NodeID("BUILTIN", node.name, node.lineno, node.col_offset),
                                   name=node.name,
                                   klass=self.scopes[self.current_class].symbol.node)
            self.scopes[self.current_class].class_variables[node.name] = [symbol]

    def get_code_from_file(file_path):
        with open(file_path, 'r') as file:
            code = file.read()
        return code

    def to_str(d: dict[str, ClassScope]) -> dict:
        return {"'" + ke + "'": repr(va) for ke, va in d.items()}

    sc = ScopesBuilder()
    walker = ASTWalker(sc)

    code = get_code_from_file(r"C:\Users\Lukas Radermacher\AppData\Local\JetBrains\PyCharm2023.3\python_stubs\-1907337602\builtins.py")
    module = astroid.parse(code)

    walker.walk(module)

    res = {}
    for k, v in sc.scopes.items():
        if k in class_dict:
            res[k] = v

    with open(r"C:\Users\Lukas Radermacher\Desktop\Results\Tests\class_scopes.json", 'w') as file:
        json.dump(to_str(res), file, indent=2)
        # for key, value in res_dict.items():
        #     if key in class_dict:
        #         file.write(f"'{key}': ClassScope(GlobalVariable({value['symbol']}),\n [],\n None,\n LocalVariable({{{value['class_variables']}}})\n)\n")

    print("")

import builtins
import json
from pathlib import Path
from typing import Any

import ijson
import pandas as pd

_BUILTINS = set(dir(builtins))


def evaluate_results(data: Any, file: str, to_console: bool = False) -> dict[str, ]:
    """Evaluate the results of the purity analysis.

    Parameters
    ----------
    data : str
        The path to the purity analysis results file.
    """
    count_pure: int = 0
    count_impure: int = 0
    count_reasons: dict[str, int] = {}
    count_reasons_specified: dict[str, int] = {}
    count_reasons_without_propagation: dict[str, int] = {}
    count_reasons_specified_without_propagation: dict[str, int] = {}

    impure_because_unknown_call: dict[str, bool] = {}
    unknown_calls: dict[str, int] = {}
    unknown_calls_unknown: dict[str] = {}
    total_reasons: int = 0
    missing_origin: int = 0


    for module in data.values():
        for fun_name, function in module.items():
            if function["purity"] == "Pure":
                count_pure += 1
            elif function["purity"] == "Impure":
                count_impure += 1

                for reason in function["reasons"]:
                    total_reasons += 1
                    res = reason["result"]
                    count_reasons[res] = count_reasons.get(res, 0) + 1
                    if res == "UnknownCall":
                        reason_name = reason["reason"].split(".")[1]
                        unknown_calls[reason_name] = unknown_calls.get(reason_name, 0) + 1
                        if reason_name == "UNKNOWN":
                            unknown_calls_unknown[fun_name] = reason_name
                        impure_because_unknown_call[fun_name] = True
                    else:
                        impure_because_unknown_call[fun_name] = False

                    specified_res = reason["reason"].split(".")[0]
                    count_reasons_specified[specified_res] = count_reasons_specified.get(specified_res, 0) + 1

                    if reason["origin"] is None:
                        missing_origin += 1

                    if reason["origin"] == fun_name:
                        count_reasons_without_propagation[res] = count_reasons_without_propagation.get(res, 0) + 1
                        count_reasons_specified_without_propagation[specified_res] = count_reasons_specified_without_propagation.get(specified_res, 0) + 1

        unknown_calls = dict(sorted(unknown_calls.items(), key=lambda item: item[1], reverse=True))
        total_reasons_without_propagation = sum(count_reasons_without_propagation.values())

    file_results = {"Name": file,
                    "Number of modules": len(data),
                    "Total functions": count_pure + count_impure,
                    "Pure functions": count_pure,
                    "Impure functions": count_impure,
                    "Reasons": count_reasons,
                    "Specified Reasons": count_reasons_specified,
                    "Reasons without propagation": count_reasons_without_propagation,
                    "Specified Reasons without propagation": count_reasons_specified_without_propagation,
                    "UnknownCalls Reasons": unknown_calls,
                    "UNKNOWN UnknownCalls": unknown_calls_unknown,
                    "Impure because UnknownCall": len({k: v for k, v in impure_because_unknown_call.items() if v}),
                    "Total Reasons": total_reasons,
                    "Total Reasons (without propagation)": total_reasons_without_propagation,
                    "Missing origin": missing_origin,
                    "Missing origin percentage": missing_origin / total_reasons * 100 if total_reasons > 0 else 0}

    if to_console:
        print(f"Results for {file}:")
        print(f"Number of modules: {len(data)}")
        print(f"Total functions: {count_pure + count_impure}")
        print(f"Pure functions: {count_pure}")
        print(f"Impure functions: {count_impure}")
        print("\nReasons:")
        for reason, count in count_reasons.items():
            print(f"{reason}: {count}")

        print("\nSpecified Reasons:")
        for reason, count in count_reasons_specified.items():
            print(f"{reason}: {count}")

        print("\nReasons without propagation:")
        for reason, count in count_reasons_without_propagation.items():
            print(f"{reason}: {count}")

        print("\nSpecified Reasons without propagation:")
        for reason, count in count_reasons_specified_without_propagation.items():
            print(f"{reason}: {count}")

        print("\nUnknownCalls Reasons:")
        for reason, count in unknown_calls.items():
            print(f"{reason}: {count}")

        res = {k: v for k, v in impure_because_unknown_call.items() if v}
        print(f"\nImpure because UnknownCall: {len(res)}")

        print(f"\nTotal Reasons: {total_reasons}, \nTotal Reasons (without propagation): {total_reasons_without_propagation}")
        print(f"\nMissing origin: {missing_origin} => {missing_origin / total_reasons * 100:.2f}%")

    return file_results


def clear_results(file: str) -> None:
    with open(file) as f:
        results = json.load(f)
        new_results = {}
        for module_name, module in results.items():
            new_results[module_name] = {}
            for function in module:
                new_results[module_name][function] = {
                    "purity": "Pure",
                }

    path = Path(r"C:\Users\Lukas Radermacher\Desktop\Results").joinpath("cleared_" + file)
    with path.open("w") as f:
        json.dump(new_results, f, indent=2)


def compare_results(expected: Any, actual: Any, result_name: str, to_console: bool = False) -> dict[str | Any, str | int | float | Any]:
    tn = 0
    tp = 0
    fn = 0
    fp = 0

    for module_name, module in expected.items():
        for function_name, function in module.items():
            if function["purity"] == actual[module_name][function_name]["purity"]:
                if function["purity"] == "Pure":
                    tp += 1  # Expected pure, actual pure
                else:
                    tn += 1  # Expected impure, actual impure

            if function["purity"] != actual[module_name][function_name]["purity"]:
                if function["purity"] == "Pure":
                    fn += 1  # Expected pure, actual impure
                else:
                    fp += 1  # Expected impure, actual pure

    if to_console:
        print(f"Total equal results: {tn + tp} (True negatives: {tn}, True positives: {tp})")
        print(f"Total different results: {fn + fp} (False negatives: {fn}, False positives: {fp})")
        print(f"Accuracy: {(tp + tn) / (tp + tn + fp + fn) * 100:.2f}%")
        print(f"Precision: {tp / (tp + fp) * 100:.2f}%")
        print(f"Recall: {tp / (tp + fn) * 100:.2f}%")
        print(f"F1-Score: {2 * tp / (2 * tp + fp + fn) * 100:.2f}%")

    return {"Name": result_name,
            "Total equal results": tn + tp,
            "True negatives": tn,
            "True positives": tp,
            "Total different results": fn + fp,
            "False negatives": fn,
            "False positives": fp,
            "Accuracy": (tp + tn) / (tp + tn + fp + fn) * 100,
            "Precision": tp / (tp + fp) * 100,
            "Recall": tp / (tp + fn) * 100,
            "F1-Score": 2 * tp / (2 * tp + fp + fn) * 100}


def compare_reasons(expected: Any, expected_name: str, actual: Any, actual_name: str, to_console: bool = False) -> dict[str, int | str]:
    missing_reasons = 0
    missing_reasons_wrong_purity = 0
    extra_reasons = 0
    extra_reasons_wrong_purity = 0

    # print the names of the missing functions
    for module_name, module in actual.items():
        for function_name, function in module.items():
            if function_name not in expected[module_name]:
                print(f"MISSING FUNCTION IN RESULT: {function_name}")


    # Check the reasons that were expected but are missing
    for module_name, module in expected.items():
        for function_name, function in module.items():
            if function["purity"] == "Impure":
                if function["purity"] == actual[module_name][function_name]["purity"]:  # both impure
                    for reason in function["reasons"]:
                        short_reason = (reason["result"], reason["reason"])
                        short_other = [(x["result"], x["reason"]) for x in actual[module_name][function_name]["reasons"]]
                        if short_reason not in short_other:
                            # print(f"MISSING REASON IN RESULT {function_name}: {reason}")
                            missing_reasons += 1


                elif function["purity"] != actual[module_name][function_name]["purity"]:  # expected impure, actual pure
                    for reason in function["reasons"]:
                        # print(f"MISSING REASON IN RESULT AND WRONG PURITY !!!VERY BAD!!! {function_name}: {reason}")
                        missing_reasons_wrong_purity += 1
                        print(f"MISSING REASON IN RESULT AND WRONG PURITY !!!VERY BAD!!! {function_name}: {reason}")

    for module_name, module in actual.items():
        for function_name, function in module.items():
            if function["purity"] == "Impure":
                if function["purity"] == expected[module_name][function_name]["purity"]:  # both impure
                    for reason in function["reasons"]:
                        short_reason = (reason["result"], reason["reason"])
                        short_other = [(x["result"], x["reason"]) for x in
                                       expected[module_name][function_name]["reasons"]]
                        if short_reason not in short_other:
                            # print(f"EXTRA REASON IN RESULT {function_name}: {reason}")
                            extra_reasons += 1


                elif function["purity"] != expected[module_name][function_name]["purity"]:  # expected pure, actual impure
                    for reason in actual[module_name][function_name]["reasons"]:
                        # print(f"EXTRA REASON IN RESULT AND WRONG PURITY {function_name}: {reason}")
                        extra_reasons_wrong_purity += 1



    if to_console:
        print(f"\n\nResults for {expected_name} and {actual_name}:")
        if missing_reasons_wrong_purity > 0:
            print("!!!FALSE POSITIVE ALARM!!!")
        print(f"Missing reasons: {missing_reasons}")
        print(f"Missing reasons with wrong purity: {missing_reasons_wrong_purity}")
        print(f"Extra reasons: {extra_reasons}")
        print(f"Extra reasons with wrong purity: {extra_reasons_wrong_purity}")

    return {"Name": actual_name,
            "Missing reasons": missing_reasons,
            "Missing reasons with wrong purity": missing_reasons_wrong_purity,
            "Extra reasons": extra_reasons,
            "Extra reasons with wrong purity": extra_reasons_wrong_purity}


def flatten_dict(d, parent_key="", sep="_"):
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def to_excel(files: list[tuple[str, str]], out_path: str) -> None:
    df = pd.DataFrame()
    res_d: dict[str, pd.DataFrame] = {}
    for file in files:
        result = get_data(file[1])
        comp_res, comp_reasons = None, None
        eval_res = evaluate_results(result, file[1])
        if file[0] != "":
            expected = get_data(file[0])
            try:
                comp_res = compare_results(expected, result, file[1], True)
            except KeyError:
                comp_res = None
            try:
                comp_reasons = compare_reasons(expected, file[0], result, file[1], True)
            except KeyError:
                comp_reasons = None
        flattened_res = flatten_dict(eval_res)
        res_d[file[1]] = pd.DataFrame(flattened_res, index=[0]).T
        # print(df)
        if comp_res:
            eval_res = {**eval_res, **comp_res}
        if comp_reasons:
            eval_res = {**eval_res, **comp_reasons}

        df = df._append(eval_res, ignore_index=True)

    with pd.ExcelWriter(f"{out_path}results_2.xlsx") as writer:
        df.to_excel(writer, sheet_name="Results", index=False)
        for f, result in res_d.items().__reversed__():
            sheet_name = f.split("/")[-1]
            result.to_excel(writer, sheet_name=sheet_name)

def get_data(file: str, simple_mode: bool = True) -> Any:
    if not simple_mode:
        result = []
        with open(file + ".json") as f:

            objects = ijson.items(f, "safeds.data.image.containers._image")

            for obj in objects:
                result.append(obj)

            parser = ijson.parse(f)
            #
            # # Initialize variables to track the current context
            # current_key = None
            # current_object = None
            #
            # try:
            #     # Iterate over each event in the parser
            #     for prefix, event, value in parser:
            #         # Check if the current prefix represents an object key
            #         if event == 'start_map':
            #             current_key = prefix
            #             current_object = {}
            #         elif event == 'map_key':
            #             current_key = value
            #         # Check if the current prefix represents a string value
            #         elif event == 'string':
            #             if current_object is not None:
            #                 current_object[current_key] = value
            #         # Check if the current prefix represents the end of an object
            #         elif event == 'end_map':
            #             if current_key == "safeds.data.image.containers._image":
            #                 result.append(current_object)
            #             current_object = None
            # except ijson.common.IncompleteJSONError as e:
            #     print("Encountered incomplete JSON:", e)


        # Convert the processed data to a DataFrame
        return pd.DataFrame(result)

    else:
        with open(file + ".json") as f:
            return json.load(f)

if __name__ == "__main__":

    def analyze_safe_ds():
        # evaluate_results("safe-ds__api_purity_4.json")
        # print("\n__________________________\n")
        # evaluate_results("safe-ds__api_purity_5.json")
        # print("\n__________________________\n")
        # evaluate_results("expected_safe-ds__api_purity_6.json")
        # print("\n__________________________\n")
        # evaluate_results("safe-ds__api_purity_6.json")
        # print("\n__________________________\n")
        # evaluate_results("safe-ds__api_purity_8.json")  # Implemented Builtin superclasses (hardcoded)
        # print("\n__________________________\n")
        # evaluate_results("safe-ds__api_purity_9.json")  # Added purity results for all Builtin functions (hardcoded)
        # print("\n__________________________\n")
        # evaluate_results("safe-ds__api_purity_15.json", True)  # Added purity results for set, list, dict methods (hardcoded)
        # clear_results("safe-ds__api_purity_22.json")
        # evaluate_results("safe-ds__api_purity_20.json", True)  # Added purity results for set, list, dict methods (hardcoded)



        # print("\n__________________________\n")
        # compare_results("expected_safe-ds__api_purity_6.json", "safe-ds__api_purity_6.json")
        # print("\n__________________________\n")
        # compare_results("expected_safe-ds__api_purity_4.json", "safe-ds__api_purity_4.json")
        # print("\n__________________________\n")
        # compare_results("expected_safe-ds__api_purity_6.json", "safe-ds__api_purity_6.json")
        # print("\n__________________________\n")
        # compare_results("expected_safe-ds__api_purity_8.json", "safe-ds__api_purity_8.json")
        # print("\n__________________________\n")
        # compare_results("expected_safe-ds__api_purity_8.json", "safe-ds__api_purity_9.json")
        # print("\n__________________________\n")
        # compare_results("expected_safe-ds__api_purity_8.json", "safe-ds__api_purity_10.json")
        # compare_results("expected_safe-ds__api_purity_8.json", "safe-ds__api_purity_9.json", True)
        # compare_reasons("expected_safe-ds__api_purity_8.json", "safe-ds__api_purity_9.json", True)
        # print("\n__________________________\n")
        # compare_results("SafeDs/expected_safe-ds__api_purity_22.json", "SafeDs/safe-ds__api_purity_24.json", True)
        # compare_reasons("SafeDs/expected_safe-ds__api_purity_22.json", "SafeDs/safe-ds__api_purity_24.json", True)
        # print("\n__________________________\n")
        # compare_results("SafeDs/expected_safe-ds__api_purity_22.json", "SafeDs/safe-ds__api_purity_25.json", True)
        # compare_reasons("SafeDs/expected_safe-ds__api_purity_22.json", "SafeDs/safe-ds__api_purity_25.json", True)
        # print("\n__________________________\n")
        # compare_results("SafeDs/expected_safe-ds__api_purity_22.json", "SafeDs/safe-ds__api_purity_26.json", True)
        # compare_reasons("SafeDs/expected_safe-ds__api_purity_22.json", "SafeDs/safe-ds__api_purity_26.json", True)
        # # print("\n__________________________\n")
        # # compare_results("expected_safe-ds__api_purity_22.json", "safe-ds__api_purity_27.json", True)
        # # compare_reasons("expected_safe-ds__api_purity_22.json", "safe-ds__api_purity_27.json", True)
        # print("\n__________________________\n")
        # compare_results("SafeDs/expected_safe-ds__api_purity_22.json", "SafeDs/safe-ds__api_purity_29.json", True)
        # compare_reasons("SafeDs/expected_safe-ds__api_purity_22.json", "SafeDs/safe-ds__api_purity_29.json", True)

        # compare_results("expected_test_module__api_purity.json", "test_module__api_purity.json")
        # compare_reasons("expected_test_module__api_purity.json", "test_module__api_purity.json")

        files = [
            # "safe-ds__api_purity_4",
            # "safe-ds__api_purity_5",
            ("SafeDs/expected_safe-ds__api_purity_6", "SafeDs/safe-ds__api_purity_6"),
            ("SafeDs/expected_safe-ds__api_purity_8", "SafeDs/safe-ds__api_purity_8"),  # Implemented Builtin superclasses (hardcoded)
            ("SafeDs/expected_safe-ds__api_purity_8", "SafeDs/safe-ds__api_purity_9"),  # Added purity results for all Builtin functions (hardcoded)
            ("SafeDs/expected_safe-ds__api_purity_10", "SafeDs/safe-ds__api_purity_10"),  # Added purity results for set, list, dict methods (hardcoded)
            ("SafeDs/expected_safe-ds__api_purity_10", "SafeDs/safe-ds__api_purity_11"),  # Test run to check determinism
            ("SafeDs/expected_safe-ds__api_purity_10", "SafeDs/safe-ds__api_purity_12"),  # Test run to check determinism
            ("SafeDs/expected_safe-ds__api_purity_10", "SafeDs/safe-ds__api_purity_13"),  # Test run to check determinism
            ("SafeDs/expected_safe-ds__api_purity_10", "SafeDs/safe-ds__api_purity_14"),  # These are the results without the super cycle bug
            ("SafeDs/expected_safe-ds__api_purity_10", "SafeDs/safe-ds__api_purity_15"),  # Package Analysis for initial files
            ("SafeDs/expected_safe-ds__api_purity_16", "SafeDs/safe-ds__api_purity_16"),  # Package Analysis for initial files with bugged return
            ("SafeDs/expected_safe-ds__api_purity_16", "SafeDs/safe-ds__api_purity_17"),  # Package Analysis for initial files with empty files
            ("SafeDs/expected_safe-ds__api_purity_16", "SafeDs/safe-ds__api_purity_18"),  # Package Analysis for initial files with empty files in debug mode
            ("SafeDs/expected_safe-ds__api_purity_19", "SafeDs/safe-ds__api_purity_19"),  # Removed duplicate reasons
            ("SafeDs/expected_safe-ds__api_purity_19", "SafeDs/safe-ds__api_purity_20"),  # Removed UnknownCalls for successfully imported classes
            ("SafeDs/expected_safe-ds__api_purity_19", "SafeDs/safe-ds__api_purity_21"),  # Added fallback for origin
            ("SafeDs/expected_safe-ds__api_purity_22", "SafeDs/safe-ds__api_purity_22"),  # Fixed call graph for nested cycles
            ("SafeDs/expected_safe-ds__api_purity_22", "SafeDs/safe-ds__api_purity_23"),  # Added @ Origin to Builtins
            ("SafeDs/expected_safe-ds__api_purity_22", "SafeDs/safe-ds__api_purity_24"),  # Detect calls of __new__ and __post_init__ on class calls
            ("SafeDs/expected_safe-ds__api_purity_22", "SafeDs/safe-ds__api_purity_25"),  # Added purity results for str methods (hardcoded)
            ("SafeDs/expected_safe-ds__api_purity_22", "SafeDs/safe-ds__api_purity_26"),  # Added purity results for str methods (hardcoded)
            ("SafeDs/expected_safe-ds__api_purity_22", "SafeDs/safe-ds__api_purity_27"),  # Arity detection astroid 3.1 (with Attribute Errors)
            ("SafeDs/expected_safe-ds__api_purity_22", "SafeDs/safe-ds__api_purity_28"),  # Arity detection astroid 2.15.6
            ("SafeDs/expected_safe-ds__api_purity_22", "SafeDs/safe-ds__api_purity_29"),  # Call graph for functions with the same name
        ]

        to_excel(files, r"D:/Ergebnisse BA/Results/SafeDs/")

    # analyze_safe_ds()
    # to_excel([("", "Seaborn/seaborn__api_purity")], "D:/Ergebnisse BA/Results/Seaborn/")
    # to_excel([("", "Scikit/scikit__api_purity")], "D:/Ergebnisse BA/Results/SciKit/")
    # to_excel([("", "Pandas/pandas__api_purity")], "D:/Ergebnisse BA/Results/Pandas/")
    to_excel([("SafeDs/safe-ds__api_purity_28", "SafeDs/safe-ds__api_purity_29")], "D:/Ergebnisse BA/Results/SafeDS/")



