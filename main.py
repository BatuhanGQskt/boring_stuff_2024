from tracetree_visitor import analyze_file
from extract_snippet import extract_code_snippet
import pprint
from hackatum.tree_handler import create_tree

def main():
    file_path = input("File path: ")
    result = analyze_file(file_path)
    pprint.pprint(result)

    selected_function = input("Function select: ")
    start_line_number, end_line_number = get_function_line(result, selected_function)
    print(f"Function '{selected_function}' starts on line: {start_line_number} and ends on line: {end_line_number}")

    code_snippet = extract_code_snippet(file_path, start_line_number, end_line_number)

    print(code_snippet)

    create_tree(result, selected_function)


def get_function_line(extractor_output, function_name):
    if function_name in extractor_output:
        return extractor_output[function_name]["start_line"], extractor_output[function_name]["end_line"]
    return None


if __name__ == "__main__":
    print('Hello')
    main()