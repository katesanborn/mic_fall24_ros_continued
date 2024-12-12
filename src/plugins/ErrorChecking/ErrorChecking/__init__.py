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

        error_report = ""
        divider = "\n=============================================================\n"
        
        def get_type(node):
            meta_types = ["LaunchFile", "Include", "Argument", "Remap", "Group", "Parameter", "rosparam", "Node", "Topic", "GroupPublisher", "GroupSubscriber", "Subscriber", "Publisher", "Machine", "Env", "Test", "rosparamBody"]
            base_type = core.get_base(node)
            while base_type and core.get_attribute(base_type, 'name') not in meta_types:
                base_type = core.get_base(base_type)
            return core.get_attribute(base_type, 'name')
        
        all_nodes = {}
        
        def at_node(node):
            node_type = get_type(node)
            
            if all_nodes.get(node_type) == None:
                all_nodes[node_type] = [node]
            else:
                all_nodes[node_type].append(node)
                
        self.util.traverse(active_node, at_node)
        
        # Check duplicate names in nodes and tests
        error_report += "TESTING FOR DUPLICATE NAMES IN NODES AND TESTS" + divider
        test_node_names = []
        for node in all_nodes.get("Node"):
            test_node_names.append(core.get_attribute(node, "name"))
            
        for test in all_nodes.get("Test"):
            test_node_names.append(core.get_attribute(test, "testName"))
            
        duplicate_names = {name for name in test_node_names if test_node_names.count(name) > 1}
        
        if len(duplicate_names) > 0:
            error_report += f"Found duplicate names in nodes and tests: {duplicate_names}\n"
        else:
            error_report += "No duplicate names\n"
            
        # Check that an argument does not have both default and value defined
        error_report += "\nTESTING FOR ERRORS IN ARG DEFINITION" + divider
        
        args_with_error = []
        
        for arg in all_nodes.get("Argument"):
            name = core.get_attribute(arg, "name")
            default = core.get_attribute(arg, "default")
            value = core.get_attribute(arg, "value")
            
            if default and value:
                args_with_error.append(name)
                
        if len(args_with_error) > 0:
            error_report += f"Found args with default and value defined: {args_with_error}\n"
        else:
            error_report += "No arg definition errors\n"
            
        # Check that arguments do not have a circular dependency
        error_report += "\nTESTING FOR CIRCULAR DEPENDENCIES IN ARG DEFINITION" + divider
        
        def get_arg_from_string(arg_string):
            pattern = r"\$\(\s*arg\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\)"
            return re.findall(pattern, arg_string)
        
        precedence = {}
        
        for arg in all_nodes.get("Argument"):
            name = core.get_attribute(arg, "name")
            default = core.get_attribute(arg, "default")
            value = core.get_attribute(arg, "value")
            
            precedence[name] = get_arg_from_string(default) + get_arg_from_string(value)
        
        try:
            ts = TopologicalSorter(precedence)
            ordered_args = list(ts.static_order())
            error_report += "No circular dependencies in args\n"
        except CycleError as e:
            error_report += f"Circular dependency in args: {e.args[1]}\n"    
        
        
        logger.info(error_report)