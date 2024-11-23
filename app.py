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
from tracetree_visitor import analyze_file
from extract_snippet import extract_code_snippet

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
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]

    if not file:
        return jsonify({"error": "File is empty"}), 400

    # Save the file to the system's temporary directory
    file_path = os.path.join(temp_dir, file.filename)
    file.save(file_path)

    print("File: ", file.file)

    # Analyze the file to get functions
    try:
        result = analyze_file(file_path)

        functions = []
        for func_name, info in result.items():
            functions.append({
                "name": func_name,
                "start_line": info["start_line"],
                "end_line": info["end_line"],
            })
        # Read the file content to send back to the frontend
        with open(file_path, "r") as f:
            file_content = f.read()
        return jsonify({"functions": functions, "file_content": file_content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        # Clean up the temporary file
        os.remove(file_path)

@app.route("/optimize-code", methods=["POST"])
def optimize_code():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    file_content = data.get("file_content")
    selected_functions = data.get("selected_functions")

    if not file_content:
        return jsonify({"error": "File content is empty"}), 400

    if not selected_functions:
        return jsonify({"error": "No functions selected"}), 400

    # Save the file content to a temporary file in the system's temp directory
    temp_filename = "temp_code.py"
    file_path = os.path.join(temp_dir, temp_filename)
    with open(file_path, "w") as f:
        f.write(file_content)

    try:
        # Analyze the file to get function line numbers
        analysis_result = analyze_file(file_path)
        print(analysis_result)

        function_changes = {}
        for func_name in selected_functions:
            

            start_line, end_line = get_function_line(analysis_result, func_name)
            if start_line is None or end_line is None:
                function_changes[func_name] = {
                    "original": "Function not found.",
                    "optimized": "Function not found."
                }
                continue

            # Extract the original function code
            original_code_snippet = extract_code_snippet(file_path, start_line, end_line)

            # Optimize the code snippet using the LLM
            optimized_code = code_optimization_chain.run(user_code=original_code_snippet)

            function_changes[func_name] = {
                "original": original_code_snippet.strip(),
                "optimized": optimized_code.strip()
            }
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        # Clean up the temporary file
        os.remove(file_path)

    return jsonify({"function_changes": function_changes})

if __name__ == "__main__":
    app.run(debug=True)