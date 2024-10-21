import ast
import sys

def find_duplicate_classes(filename):
    with open(filename, 'r') as file:
        content = file.read()

    tree = ast.parse(content)

    class_names = {}
    duplicates = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if node.name in class_names:
                duplicates.append((node.name, node.lineno, class_names[node.name]))
            else:
                class_names[node.name] = node.lineno

    return duplicates

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python check_duplicates.py <path_to_models.py>")
        sys.exit(1)

    filename = sys.argv[1]
    duplicates = find_duplicate_classes(filename)

    if duplicates:
        print("Duplicate class definitions found:")
        for name, line1, line2 in duplicates:
            print(f"Class '{name}' defined at lines {line1} and {line2}")
    else:
        print("No duplicate class definitions found.")