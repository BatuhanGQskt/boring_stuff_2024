import ast
import os
import sys

class FunctionCallExtractor(ast.NodeVisitor):
    def __init__(self, src_path, base_path=None, visited_modules=None):
        self.src_path = src_path  # Source file path
        self.base_path = base_path or os.path.dirname(src_path)  # Base path for imports
        self.function_calls = {}  # To store function calls for each function
        self.user_defined_functions = {}  # To track all user-defined function names, start and end lines
        self.imported_functions = {}  # To track imported functions and their source files
        self.current_function_stack = []  # Stack to track the current function context
        self.visited_modules = visited_modules or set()  # Modules that have been visited
        self.module_name = self._get_module_name(src_path)

    def collect_function_definitions(self, tree):
        """
        Collect all user-defined function names, start lines, and end lines, and handle imports.
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Calculate the end line by finding the maximum line number of its body
                end_line = self._get_node_end_line(node)
                # Store function name with its start and end line numbers
                self.user_defined_functions[node.name] = {
                    "start_line": node.lineno,
                    "end_line": end_line,
                    "file_path": self.src_path
                }
            elif isinstance(node, (ast.ImportFrom, ast.Import)):
                self._process_import(node)

    def _process_import(self, node):
        """
        Process import statements to track imported functions.
        """
        if isinstance(node, ast.ImportFrom):
            module_name = node.module
            if module_name:
                module_path = self._resolve_module_path(module_name)
                if module_path:
                    for alias in node.names:
                        # If importing a function or class
                        self.imported_functions[alias.name] = {
                            "file_path": module_path,
                            "module_name": module_name
                        }
                    # Recursively parse the module
                    self._parse_module(module_path)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name
                module_path = self._resolve_module_path(module_name)
                if module_path:
                    # Map the module name to its path
                    self.imported_functions[module_name] = {
                        "file_path": module_path,
                        "module_name": module_name
                    }
                    # Recursively parse the module
                    self._parse_module(module_path)

    def _resolve_module_path(self, module_name):
        """
        Resolve a module name to a file path.
        """
        # Replace '.' with os.sep and append '.py'
        module_rel_path = module_name.replace('.', os.sep) + '.py'
        module_path = os.path.join(self.base_path, module_rel_path)

        if os.path.isfile(module_path):
            return module_path
        else:
            # Module might not be in the same directory; try to find it in sys.path
            for path in sys.path:
                potential_path = os.path.join(path, module_rel_path)
                if os.path.isfile(potential_path):
                    # Exclude standard library and site-packages
                    if 'site-packages' in potential_path or 'dist-packages' in potential_path:
                        return None
                    return potential_path
        return None

    def _parse_module(self, module_path):
        """
        Recursively parse an imported module if it hasn't been parsed yet.
        """
        if module_path in self.visited_modules:
            return
        self.visited_modules.add(module_path)

        try:
            with open(module_path, 'r', encoding='utf-8') as f:
                code = f.read()
            tree = ast.parse(code)
            extractor = FunctionCallExtractor(
                src_path=module_path,
                base_path=os.path.dirname(module_path),
                visited_modules=self.visited_modules
            )
            extractor.collect_function_definitions(tree)
            extractor.visit(tree)

            # Merge the extracted data
            self.function_calls.update(extractor.function_calls)
            self.user_defined_functions.update(extractor.user_defined_functions)
            self.imported_functions.update(extractor.imported_functions)
        except Exception as e:
            print(f"Error parsing module {module_path}: {e}")

    def _get_module_name(self, file_path):
        """
        Derive a module name from a file path.
        """
        rel_path = os.path.relpath(file_path, self.base_path)
        module_name = os.path.splitext(rel_path)[0].replace(os.sep, '.')
        return module_name

    def _get_node_end_line(self, node):
        """
        Calculate the end line of a node by finding the maximum line number of its child nodes.
        """
        last_line = node.lineno
        for child in ast.walk(node):
            if hasattr(child, 'lineno'):
                last_line = max(last_line, child.lineno)
        return last_line

    def visit_FunctionDef(self, node):
        """
        Analyze function calls within a function.
        """
        func_info = self.user_defined_functions.get(node.name)
        if func_info:
            end_line = func_info["end_line"]
            file_path = func_info["file_path"]
        else:
            end_line = self._get_node_end_line(node)
            file_path = self.src_path

        # Initialize a list of calls for the current function
        self.function_calls[node.name] = {
            "calls": [],
            "file_path": file_path,
            "start_line": node.lineno,
            "end_line": end_line
        }
        # Push the function onto the stack
        self.current_function_stack.append(node.name)

        # Visit the function body
        self.generic_visit(node)

        # Pop the function from the stack after visiting
        self.current_function_stack.pop()

    def visit_Call(self, node):
        """
        Process function calls within the current function.
        """
        if self.current_function_stack:
            current_function = self.current_function_stack[-1]
            func_name = self._get_func_name(node.func)

            # Skip recursive calls (direct or indirect recursion)
            if func_name in self.current_function_stack:
                return  # Do not record recursive calls

            if func_name in self.user_defined_functions:
                func_info = self.user_defined_functions[func_name]
                self.function_calls[current_function]["calls"].append({
                    "name": func_name,
                    "file_path": func_info["file_path"],
                    "start_line": func_info["start_line"],
                    "end_line": func_info["end_line"]
                })
            elif func_name in self.imported_functions:
                import_info = self.imported_functions[func_name]
                self.function_calls[current_function]["calls"].append({
                    "name": func_name,
                    "file_path": import_info["file_path"],
                    "start_line": None,  # Start line may be unavailable
                    "end_line": None     # End line may be unavailable
                })

        self.generic_visit(node)



    def _get_func_name(self, node):
        """
        Retrieve the function name from a call node.
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            # Handle calls like module.function()
            return node.attr
        else:
            return None

def analyze_file(file_path, base_path=None):
    """
    Analyze a Python file and extract function call relationships.
    """
    base_path = base_path or os.path.dirname(file_path)
    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()
    tree = ast.parse(code)
    extractor = FunctionCallExtractor(src_path=file_path, base_path=base_path)
    # First pass: Collect function definitions and imports
    extractor.collect_function_definitions(tree)
    # Second pass: Analyze function calls
    extractor.visit(tree)
    return extractor.function_calls

def extract_function_names(file_path):
    """
    Extracts all user-defined function names from a given Python file.

    Parameters:
    - file_path (str): The path to the Python file.

    Returns:
    - List[str]: A list of function names defined in the file.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        tree = ast.parse(code)
        function_names = []

        # Traverse the AST to find all FunctionDef nodes
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                function_names.append(node.name)

        return function_names

    except FileNotFoundError:
        print(f"Error: The file '{file_path}' does not exist.")
        return []
    except SyntaxError as e:
        print(f"Syntax error in file '{file_path}': {e}")
        return []
    except Exception as e:
        print(f"An error occurred while processing '{file_path}': {e}")
        return []