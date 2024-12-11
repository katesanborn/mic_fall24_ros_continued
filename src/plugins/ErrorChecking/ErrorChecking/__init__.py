"""
This is where the implementation of the plugin code goes.
The ErrorChecking-class is imported from both run_plugin.py and run_debug.py
"""
import sys
import logging
from webgme_bindings import PluginBase

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
        root_node = self.root_node
        active_node = self.active_node

        # name = core.get_attribute(active_node, 'name')

        # logger.info('ActiveNode at "{0}" has name {1}'.format(core.get_path(active_node), name))

        # core.set_attribute(active_node, 'name', 'newName')

        # commit_info = self.util.save(root_node, self.commit_hash, 'master', 'Python plugin updated the model')
        # logger.info('committed :{0}'.format(commit_info))
        
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
        logger.info("TESTING FOR DUPLICATE NAMES IN NODES AND TESTS")
        test_node_names = []
        for node in all_nodes.get("Node"):
            test_node_names.append(core.get_attribute(node, "name"))
            
        for test in all_nodes.get("Test"):
            test_node_names.append(core.get_attribute(test, "testName"))
            
        duplicate_names = {name for name in test_node_names if test_node_names.count(name) > 1}
        
        if len(duplicate_names) > 0:
            logger.error(f"Found duplicate names in nodes and tests: {duplicate_names}")
        else:
            logger.info("No duplicate names")
            
        # Check that an argument does not have both default and value defined
        logger.info("TESTING FOR ERRORS IN ARG DEFINITION")
        
        args_with_error = []
        
        for arg in all_nodes.get("Argument"):
            name = core.get_attribute(arg, "name")
            default = core.get_attribute(arg, "default")
            value = core.get_attribute(arg, "value")
            
            if default and value:
                args_with_error.append(name)
                
        if len(args_with_error) > 0:
            logger.error(f"Found args with default and value defined: {args_with_error}")
        else:
            logger.info("No arg definition errors")
            
            