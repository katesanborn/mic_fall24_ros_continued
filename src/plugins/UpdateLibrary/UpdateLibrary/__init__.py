"""
This is where the implementation of the plugin code goes.
The UpdateLibrary-class is imported from both run_plugin.py and run_debug.py
"""
import sys
import logging
from webgme_bindings import PluginBase
import json

# Setup a logger
logger = logging.getLogger('UpdateLibrary')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)  # By default it logs to stderr..
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class UpdateLibrary(PluginBase):
    def main(self):
        core = self.core
        root_node = self.root_node
        active_node = self.active_node
        
        # Load library config
        config = self.get_current_config()
        library_config = self.get_file(config['file'])
        
        # Find libraries for node, test, and include and load current elements
        all_children = core.load_sub_tree(active_node)
        
        node_lib = next((child for child in all_children if core.get_attribute(child, "name") == "NodeLibrary"), None)
        if not node_lib:
            logger.error("NodeLibrary not found.")
            return
        
        test_lib = next((child for child in all_children if core.get_attribute(child, "name") == "TestLibrary"), None)
        if not test_lib:
            logger.error("TestLibrary not found.")
            return
        
        include_lib = next((child for child in all_children if core.get_attribute(child, "name") == "IncludeLibrary"), None)
        if not include_lib:
            logger.error("IncludeLibrary not found.")
            return

        logger.info(f"Node library: {node_lib}")
        logger.info(f"Test library: {test_lib}")
        logger.info(f"Include library: {include_lib}")
        
        node_lib_children = core.load_children(node_lib)
        
        test_lib_children = core.load_children(test_lib)
        
        include_lib_children = core.load_children(include_lib)
        
        # Delete current library contents
        for node in node_lib_children:
            core.delete_node(node)
            
        for test in test_lib_children:
            core.delete_node(test)
            
        for include in include_lib_children:
            core.delete_node(include)
            
        # Set up config as json
        library_config_json = json.loads(library_config)
        
        # Parse json to build libraries
        for package in library_config_json:
            for node in package["nodes"]:
                # Creating a new node
                new_node = core.create_child(node_lib, self.META.get("Node", None))
                core.set_attribute(new_node, "name", node["node"])
                core.set_attribute(new_node, "type", node["node"])
                core.set_attribute(new_node, "pkg", package["package"])
                
                # Creating a new test
                new_test = core.create_child(test_lib, self.META.get("Test", None))
                core.set_attribute(new_test, "testName", node["node"])
                core.set_attribute(new_test, "name", "test_" + node["node"])
                core.set_attribute(new_test, "type", node["node"])
                core.set_attribute(new_test, "pkg", package["package"])
                
                # Adding publishers
                if node["publishers"] is not None:
                    for pub in node["publishers"]:
                        node_pub = core.create_child(new_node, self.META.get("Publisher", None))
                        core.set_attribute(node_pub, "name", pub)
                        
                        test_pub = core.create_child(new_test, self.META.get("Publisher", None))
                        core.set_attribute(test_pub, "name", pub)
                    
                # Adding subscribers
                if node["subscribers"] is not None:
                    for sub in node["subscribers"]:
                        node_sub = core.create_child(new_node, self.META.get("Subscriber", None))
                        core.set_attribute(node_sub, "name", sub)
                        
                        test_sub = core.create_child(new_test, self.META.get("Subscriber", None))
                        core.set_attribute(test_sub, "name", sub)
            
            for launch_file in package["launch_files"]:
                new_include = core.create_child(include_lib, self.META.get("Include", None))
                core.set_attribute(new_include, "name", f"$(find {package["package"]})/" + launch_file["relative_path"])
        
        # Save updates
        new_commit_hash = self.util.save(core.load_root(self.project.get_root_hash(self.commit_hash)), self.commit_hash)    
        self.project.set_branch_hash(
            branch_name=self.branch_name,
            new_hash=new_commit_hash["hash"],
            old_hash=self.commit_hash
        )