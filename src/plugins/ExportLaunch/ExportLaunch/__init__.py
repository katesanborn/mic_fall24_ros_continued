"""
This is where the implementation of the plugin code goes.
The ExportLaunch-class is imported from both run_plugin.py and run_debug.py
"""
import sys
import logging
from webgme_bindings import PluginBase
import re
import textwrap
from graphlib import TopologicalSorter
from html import escape

# Setup a logger
logger = logging.getLogger('ExportLaunch')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)  # By default it logs to stderr..
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class ExportLaunch(PluginBase):
    def main(self):
        active_node = self.active_node
        core = self.core
        logger = self.logger
        
        # Nodes in project that have been traversed
        visited_nodes = []
        # Meta types that will not be included in the launch file
        ignore_meta_type = ["GroupPublisher", "GroupSubscriber", "Subscriber", "Topic", "Publisher"]
        
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
        
        def get_arg_from_string(arg_string: str) -> list:
            """Extract all names in string in form $(arg name)

            Args:
                arg_string (str): String to check for arguments

            Returns:
                list: list of arguments found in string (if any)
            """      
            pattern = r"\$\(\s*arg\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\)"
            return re.findall(pattern, arg_string)
        
        def order_args(nodes: list) -> list:
            """Sorts the args in the list of nodes so that they are ordered by precedence dependencies

            Args:
                nodes (list): All nodes to sort

            Returns:
                list: All nodes with args correctly ordered according to dependencies
            """            
            args = [n for n in nodes if get_type(n) == "Argument"]
            not_args = [n for n in nodes if get_type(n) != "Argument"]
            
            # Stores all arguments and the arguments that they depend on
            precedence = {}
            # Stores all arguments by name
            arg_dict = {}
            
            for arg in args:
                name = core.get_attribute(arg, "name")
                default = core.get_attribute(arg, "default")
                value = core.get_attribute(arg, "value")
                
                precedence[name] = get_arg_from_string(default) + get_arg_from_string(value)
                arg_dict[name] = arg
            
            try:
                ts = TopologicalSorter(precedence)
                ordered_args = list(ts.static_order())
                args = [arg_dict[arg_name] for arg_name in ordered_args]
            except:
                logger.error("Circular dependency in args")
            
            return args + not_args
        
        def sort_tags(node: dict) -> float:
            """Returns a number rank to sort the tags in a preferred order

            Args:
                node (dict): A node in the project

            Returns:
                float: Rank for ordering of node
            """            
            if get_type(node) == "Argument":
                return 1
            if get_type(node) == "rosparam":
                return 2
            if get_type(node) == "Parameter":
                return 3
            if get_type(node) == "Env":
                return 4
            if get_type(node) == "Remap":
                return 5
            if get_type(node) == "Include":
                return 6
            if get_type(node) == "Group":
                return 7
            if get_type(node) == "Machine":
                return 8
            if get_type(node) == "Node":
                return 9
            if get_type(node) == "Test":
                return 10
            
            return 100
        
        def xml_generator(activeNode: dict, indent = 0, topLevel = True) -> str:
            """Generates the launch file in XML format

            Args:
                activeNode (dict): Node in projec to parse to generate launch file
                indent (int, optional): Number of spaces to indent current tag. Defaults to 0.
                topLevel (bool, optional): Whether or not the current node is the top-level launch file node. Defaults to True.

            Returns:
                str: Launch file in XML format
            """            
            result = ""
            node_path = core.get_path(activeNode)   
            
            if topLevel:
                result += " " * indent + "<launch>\n"
                
            if node_path in visited_nodes:
                return result + '\n</launch>'
            
            visited_nodes.append(node_path)
            children = core.load_children(activeNode)
            
            children = order_args(children)
            children = sorted(children, key = lambda x: sort_tags(x))
            
            for child in children:
                child_name = core.get_attribute(child, 'name')
                base_name = get_type(child)
                
                if base_name in ignore_meta_type:
                    continue
                
                if base_name == "Argument":
                    attributes = []
                    
                    arg_name = core.get_attribute(child, 'name')
                    arg_value = core.get_attribute(child, 'value')
                    default = core.get_attribute(child, 'default')
                    doc = core.get_attribute(child, 'doc')
                    if_attr = core.get_attribute(child, 'if')
                    unless = core.get_attribute(child, 'unless')

                    if arg_name:
                        attributes.append(f'name="{escape(arg_name)}"')
                    if arg_value:
                        attributes.append(f'value="{escape(arg_value)}"')
                    if default:
                        attributes.append(f'default="{escape(default)}"')
                    if doc:
                        attributes.append(f'doc="{escape(doc)}"')
                    if if_attr:
                        attributes.append(f'if="{escape(if_attr)}"')
                    if unless:
                        attributes.append(f'unless="{escape(unless)}"')
                    
                    attribute_string = " ".join(attributes)
                    
                    result += f"{' ' * (indent + 2)}<arg {attribute_string}/>\n"
                
                elif base_name == "Node":
                    attributes = []
                    
                    pkg = core.get_attribute(child, 'pkg')
                    node_type = core.get_attribute(child, 'type')
                    args = core.get_attribute(child, 'args')
                    respawn = core.get_attribute(child, 'respawn')
                    clear_params = core.get_attribute(child, 'clear_params')
                    cwd = core.get_attribute(child, 'cwd')
                    launch_prefix = core.get_attribute(child, 'launch-prefix')
                    ns = core.get_attribute(child, 'ns')
                    output = core.get_attribute(child, 'output')
                    required = core.get_attribute(child, 'required')
                    respawn_delay = core.get_attribute(child, 'respawn_delay')
                    machine = core.get_attribute(child, 'machine')
                    if_attr = core.get_attribute(child, 'if')
                    unless = core.get_attribute(child, 'unless')
                    
                    if pkg:
                        attributes.append(f'pkg="{escape(pkg)}"')
                    if node_type:
                        attributes.append(f'type="{escape(node_type)}"')
                    if args:
                        attributes.append(f'args="{escape(args)}"')
                    if respawn:
                        attributes.append(f'respawn="{str(respawn).lower()}"')
                    if respawn == True and respawn_delay != 0:
                        attributes.append(f'respawn_delay="{respawn_delay}"')
                    if clear_params:
                        attributes.append(f'clear_params="{str(clear_params).lower()}"')
                    if cwd:
                        attributes.append(f'cwd="{escape(cwd)}"')
                    if launch_prefix:
                        attributes.append(f'launch-prefix="{escape(launch_prefix)}"')
                    if ns:
                        attributes.append(f'ns="{escape(ns)}"')
                    if output:
                        attributes.append(f'output="{escape(output)}"')
                    if required == False:
                        attributes.append(f'required="{str(required).lower()}"')
                    if machine:
                        attributes.append(f'machine="{escape(machine)}"')
                    if if_attr:
                        attributes.append(f'if="{escape(if_attr)}"')
                    if unless:
                        attributes.append(f'unless="{escape(unless)}"')
                    
                    attribute_string = " ".join(attributes)
                    
                    result += f"{' ' * (indent + 2)}<node name=\"{child_name}\" {attribute_string}>\n"
                    result += xml_generator(child, indent + 4, topLevel = False)
                    result += f"{' ' * (indent + 2)}</node>\n"

                elif base_name == "Remap":
                    attributes = []
                    
                    remap_from = core.get_attribute(child, 'from')
                    remap_to = core.get_attribute(child, 'to')
                    if_attr = core.get_attribute(child, 'if')
                    unless = core.get_attribute(child, 'unless')
                        
                    if remap_from:
                        attributes.append(f'from="{escape(remap_from)}"')
                    if remap_to:
                        attributes.append(f'to="{escape(remap_to)}"')
                    if if_attr:
                        attributes.append(f'if="{escape(if_attr)}"')
                    if unless:
                        attributes.append(f'unless="{escape(unless)}"')
                    
                    attribute_string = " ".join(attributes)
                        
                    result += f"{' ' * (indent + 2)}<remap {attribute_string}/>\n"
                
                elif base_name == "Include":
                    attributes = []
                    
                    file_name = core.get_attribute(child, 'name')
                    clear_params = core.get_attribute(child, 'clear_params')
                    ns = core.get_attribute(child, "ns")
                    pass_all_args = core.get_attribute(child, "pass_all_args")
                    if_attr = core.get_attribute(child, 'if')
                    unless = core.get_attribute(child, 'unless')

                    if file_name:
                        attributes.append(f'file="{escape(file_name)}"')
                    if clear_params:
                        attributes.append(f'clear_params="{str(clear_params).lower()}"')
                    if ns:
                        attributes.append(f'ns="{escape(ns)}"')
                    if pass_all_args:
                        attributes.append(f'pass_all_args="{str(pass_all_args).lower()}"')
                    if if_attr:
                        attributes.append(f'if="{escape(if_attr)}"')
                    if unless:
                        attributes.append(f'unless="{escape(unless)}"')
                    
                    attribute_string = " ".join(attributes)
                    
                    result += f"{' ' * (indent + 2)}<include {attribute_string}>\n"
                    result += xml_generator(child, indent + 4, topLevel = False)          
                    result += f"{' ' * (indent + 2)}</include>\n"
                
                elif base_name == "Group":
                    attributes = []
                    
                    ns = core.get_attribute(child, 'name')
                    clear_params = core.get_attribute(child, 'clear_params')
                    if_attr = core.get_attribute(child, 'if')
                    unless = core.get_attribute(child, 'unless')
                    
                    if ns:
                        attributes.append(f'ns="{escape(ns)}"')
                    if clear_params:
                        attributes.append(f'clear_params="{str(clear_params).lower()}"')
                    if if_attr:
                        attributes.append(f'if="{escape(if_attr)}"')
                    if unless:
                        attributes.append(f'unless="{escape(unless)}"')
                    
                    attribute_string = " ".join(attributes)
                    
                    result += f"{' ' * (indent + 2)}<group {attribute_string}>\n"
                    # Recursively process children of the group
                    result += xml_generator(child, indent + 4, topLevel = False)          
                    result += f"{' ' * (indent + 2)}</group>\n"
                
                elif base_name == "Parameter":
                    attributes = []
                    
                    name = core.get_attribute(child, 'name')
                    command = core.get_attribute(child, 'command')
                    value = core.get_attribute(child, 'value')
                    binfile = core.get_attribute(child, 'binfile')
                    textfile = core.get_attribute(child, 'textfile')
                    type_attr = core.get_attribute(child, 'type')
                    if_attr = core.get_attribute(child, 'if')
                    unless = core.get_attribute(child, 'unless')
                    
                    if name:
                        attributes.append(f'name="{escape(name)}"')
                    if command:
                        attributes.append(f'command="{escape(command)}"')
                    if value:
                        attributes.append(f'value="{escape(value)}"')
                    if binfile:
                        attributes.append(f'binfile="{escape(binfile)}"')
                    if textfile:
                        attributes.append(f'textfile="{escape(textfile)}"')
                    if type_attr:
                        attributes.append(f'type="{escape(type_attr)}"')
                    if if_attr:
                        attributes.append(f'if="{escape(if_attr)}"')
                    if unless:
                        attributes.append(f'unless="{escape(unless)}"')
                        
                    attribute_string = " ".join(attributes)
                    
                    result += f"{' ' * (indent + 2)}<param {attribute_string}/>\n"
                
                elif base_name == "rosparam":
                    attributes = []
                    
                    name = core.get_attribute(child, 'name')
                    command = core.get_attribute(child, 'command')
                    file = core.get_attribute(child, 'file')
                    param = core.get_attribute(child, 'param')
                    ns = core.get_attribute(child, 'ns')
                    subst_value = core.get_attribute(child, 'subst_value')
                    if_attr = core.get_attribute(child, 'if')
                    unless = core.get_attribute(child, 'unless')
                    
                    if command:
                        attributes.append(f'command="{escape(command)}"')
                    if file:
                        attributes.append(f'file="{escape(file)}"')
                    if param:
                        attributes.append(f'param="{escape(param)}"')
                    if ns:
                        attributes.append(f'ns="{escape(ns)}"')
                    if subst_value == False:
                        attributes.append(f'subst_value="{str(subst_value).lower()}"')
                    if if_attr:
                        attributes.append(f'if="{escape(if_attr)}"')
                    if unless:
                        attributes.append(f'unless="{escape(unless)}"')
                    
                    attribute_string = " ".join(attributes)
                    
                    result += f"{' ' * (indent + 2)}<rosparam {attribute_string}>\n"
                    result += xml_generator(child, indent + 4, topLevel = False)
                    result += f"{' ' * (indent + 2)}</rosparam>\n"
                    
                elif base_name == "Machine":
                    attributes = []
                    
                    name = core.get_attribute(child, 'name')
                    address = core.get_attribute(child, 'address')
                    env_loader = core.get_attribute(child, 'env-loader')
                    default = core.get_attribute(child, 'default')
                    user = core.get_attribute(child, 'user')
                    password = core.get_attribute(child, 'password')
                    timeout = core.get_attribute(child, 'timeout')
                    if_attr = core.get_attribute(child, 'if')
                    unless = core.get_attribute(child, 'unless')
                    
                    if name:
                        attributes.append(f'name="{escape(name)}"')
                    if address:
                        attributes.append(f'address="{escape(address)}"')
                    if env_loader:
                        attributes.append(f'env-loader="{escape(env_loader)}"')
                    if default:
                        attributes.append(f'default="{escape(default)}"')
                    if user:
                        attributes.append(f'user="{escape(user)}"')
                    if password:
                        attributes.append(f'password="{escape(password)}"')
                    if timeout != 10:
                        attributes.append(f'timeout="{timeout}"')
                    if if_attr:
                        attributes.append(f'if="{escape(if_attr)}"')
                    if unless:
                        attributes.append(f'unless="{escape(unless)}"')
                        
                    attribute_string = " ".join(attributes)
                        
                    result += f"{' ' * (indent + 2)}<machine {attribute_string}>\n"           
                    result += xml_generator(child, indent + 4,topLevel = False)
                    result += f"{' ' * (indent + 2)}</machine>\n"
                
                elif base_name == "Env":
                    attributes = []
                    
                    name = core.get_attribute(child, 'name')
                    value = core.get_attribute(child, 'value')
                    if_attr = core.get_attribute(child, 'if')
                    unless = core.get_attribute(child, 'unless')
                    
                    if name:
                        attributes.append(f'name="{escape(name)}"')
                    if value:
                        attributes.append(f'value="{escape(value)}"')
                    if if_attr:
                        attributes.append(f'if="{escape(if_attr)}"')
                    if unless:
                        attributes.append(f'unless="{escape(unless)}"')
                        
                    attribute_string = " ".join(attributes)
                        
                    result += f"{' ' * (indent + 2)}<env {attribute_string}/>\n"     
                
                elif base_name == "Test":
                    attributes = []
                    
                    test_name = core.get_attribute(child, 'testName')
                    node_type = core.get_attribute(child, 'type')
                    pkg = core.get_attribute(child, 'pkg')
                    name = core.get_attribute(child, 'name')
                    args = core.get_attribute(child, 'args')
                    clear_params = core.get_attribute(child, 'clear_params')
                    cwd = core.get_attribute(child, 'cwd')
                    launch_prefix = core.get_attribute(child, 'launch-prefix')
                    ns = core.get_attribute(child, 'ns')
                    retry = core.get_attribute(child, 'retry')
                    time_limit = core.get_attribute(child, 'time-limit')
                    if_attr = core.get_attribute(child, 'if')
                    unless = core.get_attribute(child, 'unless')
                    
                    if pkg:
                        attributes.append(f'pkg="{escape(pkg)}"')
                    if test_name:
                        attributes.append(f'test-name="{escape(test_name)}"')
                    if node_type:
                        attributes.append(f'type="{escape(node_type)}"')
                    if name:
                        attributes.append(f'name="{escape(name)}"')
                    if args:
                        attributes.append(f'args="{escape(args)}"')
                    if clear_params:
                        attributes.append(f'clear_params="{str(clear_params).lower()}"')    
                    if cwd:
                        attributes.append(f'cwd="{escape(cwd)}"')
                    if launch_prefix:
                        attributes.append(f'launch-prefix="{escape(launch_prefix)}"')
                    if ns:
                        attributes.append(f'ns="{escape(ns)}"')
                    if retry:
                        attributes.append(f'retry="{retry}"')
                    if time_limit != 60:
                        attributes.append(f'time-limit="{time_limit}"')
                    if if_attr:
                        attributes.append(f'if="{escape(if_attr)}"')
                    if unless:
                        attributes.append(f'unless="{escape(unless)}"')
                        
                    attribute_string = " ".join(attributes)
                    
                    result += f"{' ' * (indent + 2)}<test {attribute_string}>\n"
                    result += xml_generator(child, indent + 4, topLevel = False)
                    result += f"{' ' * (indent + 2)}</test>\n"
                    
                elif "rosparamBody":
                    result += textwrap.indent(core.get_attribute(child, 'body'), f"{' ' * (indent + 2)}") + "\n"
                
            if topLevel:
                result += " " * indent + "</launch>\n"
            
            return result
            
        output = xml_generator(active_node)
        logger.info(f"Output:\n{output}")
        
        def clean_filename(filename: str, replacement = "_") -> str:
            """Removes invalid characters from file name

            Args:
                filename (str): File name to be cleaned
                replacement (str, optional): Character used to replace invalid characters. Defaults to "_".

            Returns:
                str: Cleaned file name
            """            
            
            # Define invalid characters for most file systems
            invalid_chars = r'[<>:"/\\|?*\x00-\x1F]'
            # Replace invalid characters with the specified replacement
            cleaned_name = re.sub(invalid_chars, replacement, filename)
            # Strip leading and trailing whitespace and replace any trailing dots or spaces
            cleaned_name = cleaned_name.strip().rstrip(". ")
            # Ensure the filename is not empty or reduced to dots/spaces
            return cleaned_name if cleaned_name else "output_launch"

        
        file_name = clean_filename(f'{core.get_attribute(active_node, 'name')}.launch')
        file_hash = self.add_file(file_name, output)
        
        logger.info(f"Output saved to file with hash: {file_hash}")