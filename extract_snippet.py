def extract_code_snippet(file_path, start_line, end_line):
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
            # Extract the desired lines
            snippet = lines[start_line - 1:end_line]
            return ''.join(snippet)
    except Exception as e:
        return f"Error: {e}"
