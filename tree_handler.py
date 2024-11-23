# Import necessary libraries
import os  # For handling file paths
from anytree import Node, RenderTree
from anytree.exporter import DotExporter
from anytree import PostOrderIter

def create_tree(data, root_func_name):
    # A dictionary to keep track of created nodes
    nodes = {}
    # Create tree starting from the specified root function
    root_node = create_node(root_func_name, nodes, data)
    if not root_node:
        print(f"Unable to create tree for function '{root_func_name}'.")
        return

    return root_node

def display_tree(root_node):
    # Render and print the tree
    print(f"Call Tree for '{root_node.name.split(' ')[0]}':")
    for pre, fill, node in RenderTree(root_node):
        print(f"{pre}{node.name}")
    print("\n" + "-"*50 + "\n")

    # Optional: Export the tree to a graphical format (requires Graphviz installed)
    # Uncomment the lines below to generate a .png file for the tree

    # DotExporter(root_node).to_picture(f"{root_node.name.split(' ')[0]}_call_tree.png")


# Function to create nodes recursively
def create_node(func_name, nodes, data):
    print("Creat node")
    if func_name in nodes:
        return nodes[func_name]
    func_data = data.get(func_name)
    if not func_data:
        print(f"Function '{func_name}' not found in data.")
        return None
    # Use os.path.basename to extract the filename
    print(func_data['file_path'])
    file_name = func_data['file_path']
    node_label = f"{func_name} ({file_name}:{func_data['start_line']}-{func_data['end_line']})"

    node = Node(node_label)
    nodes[func_name] = node
    for call in func_data['calls']:
        child_name = call['name']
        child_node = create_node(child_name, nodes, data)
        if child_node:
            child_node.parent = node
    return node

def flatten_tree(root):
    # Flatten the tree using post-order traversal
    flat_nodes = [node for node in PostOrderIter(root)]
    flat_names = [node.name for node in PostOrderIter(root)]

    return flat_nodes, flat_names