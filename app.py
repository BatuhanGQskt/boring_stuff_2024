from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import tempfile
from langchain.chat_models import ChatOpenAI
from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.chains import LLMChain
from tracetree_visitor import analyze_file, extract_function_names
from extract_snippet import extract_code_snippet

from tree_handler import create_tree, display_tree, flatten_tree
import re


app = Flask(__name__)

# Simplify CORS configuration
CORS(app, resources={r"/*": {"origins": "*"}})

# Set up environment variable for OpenAI API key
def _set_env_from_file(var: str, file_path: str):
    if not os.environ.get(var):
        try:
            with open(file_path, "r") as file:
                os.environ[var] = file.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError(f"API key file not found at {file_path}")
        except Exception as e:
            raise Exception(f"Error reading API key from file: {e}")

_set_env_from_file("OPENAI_API_KEY", "api_key.txt")

# Define the LLM and prompt template
llm = ChatOpenAI(temperature=0, model_name="gpt-4")

system_message = SystemMessagePromptTemplate.from_template(
    "You are an expert Python programmer specializing in code optimization. "
    "Given a code snippet, optimize it for efficiency and readability. "
    "Also, remember the codes that you solved or tried to optimize to further use."
    "If no code is provided, respond with 'No code provided.'. "
    "Provide the optimized code only, and don't give the exact same code as optimized."
)

human_message = HumanMessagePromptTemplate.from_template("{user_code}")

chat_prompt = ChatPromptTemplate.from_messages([system_message, human_message])

code_optimization_chain = LLMChain(llm=llm, prompt=chat_prompt)

def get_function_line(extractor_output, function_name):
    if function_name in extractor_output:
        return extractor_output[function_name]["start_line"], extractor_output[function_name]["end_line"]
    else:
        return None, None

# Use the system's temporary directory
temp_dir = tempfile.gettempdir()

# Flask routes
@app.route("/", methods=["GET"])
def home():
    return "Welcome to the Code Optimization API! Upload a file to optimize its code."

@app.route("/upload-code", methods=["POST"])
def upload_code():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    file_path = data.get("file_path")
    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "Invalid or non-existent file path."}), 400

    try:
        # Analyze the file at the given path
        functions = extract_function_names(file_path)
        print(functions)

        # Read the file content
        with open(file_path, "r") as f:
            file_content = f.read()

        return jsonify({"functions": functions, "file_content": file_content, "file_path": file_path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/optimize-code", methods=["POST"])
def optimize_code():
    data = request.get_json()
    print(data)
    if not data:
        return jsonify({"error": "No data provided"}), 400

    file_path = data.get("file_path")
    selected_function = data.get("selected_functions")

    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "Invalid or non-existent file path."}), 400

    if not selected_function:
        return jsonify({"error": "No functions selected"}), 400

    try:
        print("File path:", file_path)
        # Analyze the file at the given path
        analysis_result = analyze_file(file_path)

        print("Select: " , selected_function)
        print("Analysis: ", analysis_result)
        analysis_tree = create_tree(analysis_result, selected_function[0])

        display_tree(analysis_tree)

        flat_tree, flat_names = flatten_tree(analysis_tree)
        
        print("FLAT NAMES: ")
        print(flat_names)

        function_changes_elems = {}
        for node in flat_names:
            func_name, func_path, start_line, end_line = extract_feature_from_tree_elem(node)

            if start_line is None or end_line is None:
                function_changes_elems[func_name] = {
                    "original": "Function not found.",
                    "optimized": "Function not found."
                }


            print("Name, path, start, end: ")
            print(func_name, func_path, start_line, end_line)

            print("of the ", node)

            function_changes_elems[func_name] = [func_path, int(start_line), int(end_line)]
        
        print("FUN CHANGES: ")
        print(function_changes_elems)

        function_changes = {}

        for keys, items in function_changes_elems.items():
            original_snippet = extract_code_snippet(items[0], items[1], items[2])
            print("For func "+ str(keys) + ": ")
            print(original_snippet)

            optimized_code = code_optimization_chain.run(user_code=original_snippet)

            function_changes[keys] = {
                "original": original_snippet,
                "optimized": optimized_code
            }

            #file_path[keys] = {
            #    "start_line": items[1],
            #    "end_line": items[2],
            #    "file_path": items[0]
            #}

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"function_changes": function_changes, "updated_file_path": file_path})

@app.route("/accept-optimized-code", methods=["POST"])
def accept_optimized_code():
    data = request.get_json()

    print("Taken data: ", data)
    if not data:
        return jsonify({"error": "No data provided"}), 400

    file_path = data.get("file_path")
    start_line = int(data.get("start_line", 0))
    end_line = int(data.get("end_line", 0))
    optimized_code = data.get("optimized_code")

    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "Invalid or non-existent file path."}), 400

    if not optimized_code or start_line <= 0 or end_line <= 0:
        return jsonify({"error": "Invalid input data."}), 400

    try:
        # Use replace_lines_in_file to update the file
        replace_lines_in_file(file_path, start_line, end_line, optimized_code)
        return jsonify({"message": f"Function updated successfully in {file_path}."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def extract_feature_from_tree_elem(s):
    # Define the regular expression pattern
    pattern = r'^(?P<func_name>\w+)\s\((?P<func_path>.+):(?P<start_line>\d+)-(?P<end_line>\d+)\)$'

    # Match the pattern with the string
    match = re.match(pattern, s)

    if match:
        func_name = match.group('func_name')
        func_path = match.group('func_path')
        start_line = int(match.group('start_line'))
        end_line = int(match.group('end_line'))

        return func_name, func_path, start_line, end_line
    return None

def replace_lines_in_file(file_path, start_line, end_line, new_text):
    # Read the original file
    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Adjust line numbers for zero-based indexing
    start_idx = start_line - 1
    end_idx = end_line

    # Ensure new_text is a list of lines with newline characters
    if isinstance(new_text, str):
        new_text = new_text.splitlines(keepends=True)
    else:
        new_text = [line if line.endswith('\n') else line + '\n' for line in new_text]

    # Replace the specified lines with the new text
    lines[start_idx:end_idx] = new_text

    # Write the updated content back to the file
    with open(file_path, 'w') as file:
        file.writelines(lines)

def extract_snippet(file_path, start_line, end_line):
    try:
        # Open the file and read all lines
        with open(file_path, 'r') as file:
            lines = file.readlines()
        
        # Get the total number of lines in the file
        total_lines = len(lines)
        
        # Validate the provided line numbers
        if start_line < 1 or end_line > total_lines or start_line > end_line:
            raise ValueError("Start or end line numbers are invalid or out of range.")
        
        # Adjust indices for zero-based indexing
        start_idx = start_line - 1  # Python lists start at index 0
        end_idx = end_line          # Slicing is up to but not including end_idx
        
        # Extract the snippet
        snippet_lines = lines[start_idx:end_idx]
        
        # Join the lines into a single string
        snippet = ''.join(snippet_lines)
        
        return snippet
    
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return ''
    except Exception as e:
        print(f"An error occurred: {e}")
        return ''

if __name__ == "__main__":
    app.run(debug=True)