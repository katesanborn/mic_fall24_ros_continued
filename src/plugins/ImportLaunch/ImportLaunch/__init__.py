"""
This is where the implementation of the plugin code goes.
The ImportLaunch-class is imported from both run_plugin.py and run_debug.py
"""
import sys
import logging
import xml.etree.ElementTree as ET
import json
from webgme_bindings import PluginBase

# Setup a logger
logger = logging.getLogger('ImportLaunch')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class ImportLaunch(PluginBase):
    def validate_and_update_tag(self, tag: str) -> str:
        """Ensures the tag is lowercase for standardization, except for special cases.

        Args:
            tag (str): Tag in the XML file

        Returns:
            str: Standardized tag
        """        

        if tag.lower() == "arg":  # Special case for 'arg'
            return "argument"
        if tag.lower() == "param":
            return "parameter"
        return tag.lower()  # Default to lowercase

    def parse_ros_launch(self, xml_string: str) -> dict:
        """Parses a ROS launch file into a structured dictionary.

        Args:
            xml_string (str): XML file input represented as string

        Returns:
            dict: JSON format of XML tag information 
        """
        root = ET.fromstring(xml_string)

        def parse_element(element: ET.Element) -> dict:
            """Recursively parse an XML element into a dictionary.

            Args:
                element (ET.Element): Element in XML file

            Returns:
                dict: Element translated to dict
            """            
            tag = self.validate_and_update_tag(element.tag.split('}')[-1])  # Handle namespaces if present
            attributes = element.attrib

            # Update attributes for special cases like 'include' and 'group'
            if tag == "include" and "file" in attributes:
                attributes["name"] = attributes.pop("file")
            if tag == "group" and "ns" in attributes:
                attributes["name"] = attributes.pop("ns")
            if tag == "test" and "test-name" in attributes:
                attributes["testName"] = attributes.pop("test-name")

            parsed = {
                "tag": tag,  # Updated tag name
                "attributes": attributes,  # Attributes from the XML
                "children": [parse_element(child) for child in element]  # Recursively parse children
            }
            
            if tag == "rosparam":
                # Include text content of the rosparam tag
                parsed["text"] = element.text.strip() if element.text else ""
            
            return parsed

        return parse_element(root)

    def main(self):
        core = self.core
        active_node = self.active_node
        logger = self.logger

        config = self.get_current_config()
        input = self.get_file(config['file'])

        # Parse the ROS launch file into a structured dictionary
        launch_data = self.parse_ros_launch(input)

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

        # Ensure 'LaunchFile' type exists in the META
        if 'LaunchFile' not in self.META:
            logger.error('LaunchFile type not found in META. Ensure it exists in the meta-model.')
            return

        try:
            # Define parameters for the new LaunchFile node
            params = {
                'parent': active_node,
                'base': self.META['LaunchFile']
            }
            launch_file_node = core.create_node(params)
            core.set_attribute(launch_file_node, 'name', 'launch')
            logger.info(f'Created new LaunchFile node with name: "launch".')

            # Load the Node Library for comparison
            all_children = core.load_sub_tree(active_node)
            node_lib = next((child for child in all_children if core.get_attribute(child, "name") == "NodeLibrary"), None)

            if not node_lib:
                logger.error("NodeLibrary not found.")
                return
            
            # Load the Test Library for comparison
            all_children = core.load_sub_tree(active_node)
            test_lib = next((child for child in all_children if core.get_attribute(child, "name") == "TestLibrary"), None)

            if not test_lib:
                logger.error("TestLibrary not found.")
                return
            
            # Load the Include Library for comparison
            all_children = core.load_sub_tree(active_node)
            include_lib = next((child for child in all_children if core.get_attribute(child, "name") == "IncludeLibrary"), None)

            if not include_lib:
                logger.error("IncludeLibrary not found.")
                return

            # Cache all nodes in the node library
            lib_children = core.load_sub_tree(node_lib)
            node_library = {
                (core.get_attribute(node, "pkg"), core.get_attribute(node, "type")): node
                for node in lib_children
                if core.get_attribute(node, "pkg") and core.get_attribute(node, "type")
            }
            
            # Cache all tests in the test library
            test_lib_children = core.load_sub_tree(test_lib)
            test_library = {
                (core.get_attribute(node, "pkg"), core.get_attribute(node, "type")): node
                for node in test_lib_children
                if core.get_attribute(node, "pkg") and core.get_attribute(node, "type")
            }
            
            # Cache all includes in the include library
            include_lib_children = core.load_sub_tree(include_lib)
            include_library = {
                core.get_attribute(node, "name").replace("/", ""): node
                for node in include_lib_children
                if core.get_attribute(node, "name")
            }

            def find_node_in_library(node_data: dict) -> dict:
                """Locates node in node library

                Args:
                    node_data (dict): Node data from XML

                Returns:
                    dict: Node in WebGME
                """                
                
                pkg = node_data.get("attributes", {}).get("pkg")
                node_type = node_data.get("attributes", {}).get("type")
                return node_library.get((pkg, node_type))
            
            def find_test_in_library(test_data: dict) -> dict:
                """Locates test in test library

                Args:
                    test_data (dict): Test data from XML

                Returns:
                    dict: Test in WebGME
                """                 
                
                pkg = test_data.get("attributes", {}).get("pkg")
                test_type = test_data.get("attributes", {}).get("type")
                return test_library.get((pkg, test_type))

            def find_include_in_library(include_data: dict) -> dict:
                """Locates include in include library

                Args:
                    include_data (dict): Include data from XML

                Returns:
                    dict: Include in WebGME
                """
                name = include_data.get("attributes", {}).get("name").replace("/", "") if include_data.get("attributes", {}).get("name") else None
                return include_library.get(name)

            def copy_attributes_and_pub_sub(existing_node: dict, child_node: dict):
                """Copies all attributes and publishers/subscribers from the existing library node to the new child node.

                Args:
                    existing_node (dict): Node found in library
                    child_node (dict): Node to receive copies
                """                
                
                for attr in core.get_attribute_names(existing_node):
                    core.set_attribute(child_node, attr, core.get_attribute(existing_node, attr))

                lib_children = core.load_sub_tree(existing_node)
                new_node_children = core.load_children(child_node)

                def child_exists(child: dict, children: list) -> bool:
                    """Check if a child with the same name already exists in the new node.

                    Args:
                        child (dict): Child node to check from library
                        children (list): Existing children

                    Returns:
                        bool: Whether or not a child with the same name already exists in the new node
                    """                    
                    
                    child_name = core.get_attribute(child, "name")
                    return any(core.get_attribute(existing_child, "name") == child_name for existing_child in children)

                for lib_child in lib_children:
                    child_type = get_type(lib_child)
                    if child_type in ["Publisher", "Subscriber", "GroupPublisher", "GroupSubscriber"]:
                        if not child_exists(lib_child, new_node_children):
                            copied_node = core.copy_node(lib_child, child_node)
                            logger.info(f"Copied {core.get_attribute(copied_node, 'name')} to {core.get_attribute(child_node, 'name')}.")

            def create_child_nodes(parent_node: dict, data: dict):
                """Creates child nodes using attributes from the input data if the node does not exist in the library.

                Args:
                    parent_node (dict): WebGME parent node
                    data (dict): XML dict
                """                

                for child in data.get("children", []):
                    tag = child.get("tag").capitalize()
                    
                    if tag == "Rosparam":
                        tag = "rosparam"
                    
                    attributes = child.get("attributes", {})
                    name_attribute = attributes.get("name")

                    # Check if the node already exists in the library
                    existing_node = find_node_in_library(child)
                    
                    # Check if the test already exists in the library
                    existing_test = find_test_in_library(child)
                    
                    # Check if the include already exists in the library
                    existing_include = find_include_in_library(child)

                    if existing_node and tag == "Node":
                        logger.info(f"Node {name_attribute} found in library. Copying attributes and publishers/subscribers.")
                        child_node = core.create_child(parent_node, core.get_meta_type(existing_node))
                        copy_attributes_and_pub_sub(existing_node, child_node)
                    elif existing_test and tag == "Test":
                        logger.info(f"Test {attributes.get("testName")} found in library. Copying attributes and publishers/subscribers.")
                        child_node = core.create_child(parent_node, core.get_meta_type(existing_test))
                        copy_attributes_and_pub_sub(existing_test, child_node)
                    elif existing_include and tag == "Include":
                        logger.info(f"Include {name_attribute} found in library. Copying publishers/subscribers.")
                        child_node = core.create_child(parent_node, core.get_meta_type(existing_include))
                        copy_attributes_and_pub_sub(existing_include, child_node)
                    else:
                        child_node = core.create_child(parent_node, self.META.get(tag, None) if tag in self.META else None)
                        logger.info(f"Created new node: {name_attribute} with attributes from input.")
                        
                        if tag == "rosparam":
                            text = child.get("text", {})
                            if text:
                                rosparam_body_node = core.create_child(child_node, self.META.get("rosparamBody", None))
                                core.set_attribute(rosparam_body_node, 'body', "\n".join(line.strip() for line in text.splitlines() if line.strip()))

                    for attr, value in attributes.items():
                        attribute_value = core.get_attribute(child_node, attr)
                        
                        if isinstance(attribute_value, bool):
                            if value.lower() == "true":
                                core.set_attribute(child_node, attr, True)
                            elif value.lower() == "false":
                                core.set_attribute(child_node, attr, False)
                        else:
                            core.set_attribute(child_node, attr, value)

                    create_child_nodes(child_node, child)

            # Create child nodes from launch_data
            create_child_nodes(launch_file_node, launch_data)

            # Save the changes
            new_commit_hash = self.util.save(launch_file_node, self.commit_hash)
            self.project.set_branch_hash(
                branch_name=self.branch_name,
                new_hash=new_commit_hash["hash"],
                old_hash=self.commit_hash
            )
            logger.info("All nodes successfully created and saved.")
        except Exception as e:
            logger.error(f"Error during node creation: {str(e)}")

