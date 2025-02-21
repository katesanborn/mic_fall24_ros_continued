"""
This is where the implementation of the plugin code goes.
The ErrorChecking-class is imported from both run_plugin.py and run_debug.py
"""
import sys
import logging
from webgme_bindings import PluginBase
import re
from graphlib import TopologicalSorter, CycleError

# Setup a logger
logger = logging.getLogger('ErrorChecking')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)  # By default it logs to stderr..
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class ErrorChecking(PluginBase):
    def main(self):
        core = self.core
        active_node = self.active_node

        # Stores report of all errors for notification
        error_report = ""
        # Divides test name from result in error report
        divider = ": "
        
        def get_type(node: dict) -> str:
            """Returns the type of the WebGME node

            Args:
                node (dict): A node in the WebGME project

            Returns:
                str: The type of the node as defined in the Launch File tab in the metamodel
            """            
            meta_types = ["LaunchFile", "Include", "Argument", "Remap", "Group", "Parameter", "rosparam", "Node", "Topic", "GroupPublisher", "GroupSubscriber", "Subscriber", "Publisher", "Machine", "Env", "Test", "rosparamBody"]
            base_type = core.get_base(node)
            while base_type and core.get_attribute(base_type, 'name') not in meta_types:
                base_type = core.get_base(base_type)
            return core.get_attribute(base_type, 'name')
        
        def get_node_name(node: dict) -> str:
            """Gets name of a node including all namespaces

            Args:
                node (dict): A node in the WebGME project

            Returns:
                str: Name including namespaces
            """            
            
            name = core.get_attribute(node, "name")
            
            ns = core.get_attribute(node, "ns")
            if ns != "" and name[0] != "/":
                name = ns + "/" + name
            
            parent = core.get_parent(node)
            
            while get_type(parent) != "LaunchFile" and name[0] != "/":
                if get_type(parent) == "Group":
                    ns = core.get_attribute(parent, "name")
                    if ns != "":
                        name = ns + "/" + name
                
                parent = core.get_parent(parent)
            
            return name if name[0] != "/" else name[1:]
        
        def get_test_name(test: dict) -> str:
            """Gets name of a test including all namespaces

            Args:
                test (dict): A test in the WebGME project

            Returns:
                str: Name including namespaces
            """
            
            name = core.get_attribute(test, "testName")
            
            ns = core.get_attribute(test, "ns")
            if ns != "" and name[0] != "/":
                name = ns + "/" + name
            
            parent = core.get_parent(test)
            
            while get_type(parent) != "LaunchFile" and name[0] != "/":
                if get_type(parent) == "Group":
                    ns = core.get_attribute(parent, "name")
                    if ns != "":
                        name = ns + "/" + name
                
                parent = core.get_parent(parent)
            
            return name if name[0] != "/" else name[1:]
        
        # Dictionary to store all nodes using type as key
        all_nodes = {}
        
        def document_nodes(node: dict):
            """Stores all nodes in project in dictionary with type as key

            Args:
                node (dict): A node in the WebGME project
            """            
            node_type = get_type(node)
            
            if all_nodes.get(node_type) is None:
                all_nodes[node_type] = [node]
            else:
                all_nodes[node_type].append(node)
                
        self.util.traverse(active_node, document_nodes)
        
        # Check duplicate names in nodes and tests
        error_report += "TESTING FOR DUPLICATE NAMES IN NODES AND TESTS" + divider
        test_node_names = []
        
        if all_nodes.get("Node") is not None:
            for node in all_nodes.get("Node"):
                test_node_names.append(get_node_name(node))
            
        if all_nodes.get("Test") is not None:
            for test in all_nodes.get("Test"):
                test_node_names.append(get_test_name(test))

        # Make list of all node names that are repeated 
        duplicate_names = {name for name in test_node_names if test_node_names.count(name) > 1}
        
        if len(duplicate_names) > 0:
            error_report += f"Found duplicate names in nodes and tests: {duplicate_names} |"
        else:
            error_report += "No duplicate names |"
            
        # Check that an argument does not have both default and value defined
        error_report += "TESTING FOR ERRORS IN ARG DEFINITION" + divider
        
        # List to store all argument nodes in project with errors
        args_with_error = []
        
        # Find nodes with default and value defined and add to errors
        if all_nodes.get("Argument") is not None:
            for arg in all_nodes.get("Argument"):
                name = core.get_attribute(arg, "name")
                default = core.get_attribute(arg, "default")
                value = core.get_attribute(arg, "value")
                
                if default and value:
                    args_with_error.append(name)
                
        if len(args_with_error) > 0:
            error_report += f"Found args with default and value defined: {args_with_error} |"
        else:
            error_report += "No arg definition errors |"
            
        # Check that arguments do not have a circular dependency
        error_report += "TESTING FOR CIRCULAR DEPENDENCIES IN ARG DEFINITION" + divider
        
        def get_arg_from_string(arg_string: str) -> list:
            """Extract all names in string in form $(arg name)

            Args:
                arg_string (str): String to check for arguments

            Returns:
                list: list of arguments found in string (if any)
            """            
            pattern = r"\$\(\s*arg\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\)"
            return re.findall(pattern, arg_string)
        
        # Dictionary to store args and the args that they depend on
        precedence = {}
        
        if all_nodes.get("Argument") is not None:
            for arg in all_nodes.get("Argument"):
                name = core.get_attribute(arg, "name")
                default = core.get_attribute(arg, "default")
                value = core.get_attribute(arg, "value")
                
                precedence[name] = get_arg_from_string(default) + get_arg_from_string(value)
        
        try:
            ts = TopologicalSorter(precedence)
            ordered_args = list(ts.static_order())
            error_report += "No circular dependencies in args |"
        except CycleError as e:
            error_report += f"Circular dependency in args: {e.args[1]} |"    
        
        
        self.send_notification(error_report)