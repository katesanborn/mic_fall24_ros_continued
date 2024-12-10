"""
This is where the implementation of the plugin code goes.
The ExportLaunch-class is imported from both run_plugin.py and run_debug.py
"""
import sys
import logging
from webgme_bindings import PluginBase
import re
import textwrap

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
        
        visited_nodes = []
        ignoreMetaType = ["GroupPublisher", "GroupSubscriber", "Subscriber", "Topic", "Publisher"]
        
        def get_type(node):
            meta_types = ["LaunchFile", "Include", "Argument", "Remap", "Group", "Parameter", "rosparam", "Node", "Topic", "GroupPublisher", "GroupSubscriber", "Subscriber", "Publisher", "Machine", "Env", "Test", "rosparamBody"]
            base_type = core.get_base(node)
            while base_type and core.get_attribute(base_type, 'name') not in meta_types:
                base_type = core.get_base(base_type)
            return core.get_attribute(base_type, 'name')
        
        def sortTags(node):
            if get_type(node) == "Argument":
                return 1
            if get_type(node) == "rosparam":
                return 2
            if get_type(node) == "Parameter":
                return 3
            if get_type(node) == "Env":
                return 4
            if get_type(node) == "Include":
                return 5
            if get_type(node) == "Group":
                return 6
            if get_type(node) == "Machine":
                return 7
            if get_type(node) == "Remap":
                return 8
            if get_type(node) == "Node":
                return 9
            if get_type(node) == "Test":
                return 10
            
            return 100
        
        def xmlGenerator(activeNode, indent = 0, topLevel = True):
            result = ""
            node_path = core.get_path(activeNode)   
            
            if topLevel:
                result += " " * indent + "\n<launch>\n"
                
            if node_path in visited_nodes:
                return result + '\n</launch>'
            
            visited_nodes.append(node_path)
            children = core.load_children(activeNode)
            
            children = sorted(children, key = lambda x: sortTags(x))
            
            for child in children:
                childName = core.get_attribute(child, 'name')
                base_Name = get_type(child)
                
                if base_Name in ignoreMetaType:
                    continue
                
                if base_Name == "Argument":
                    attributes = []
                    
                    arg_name = core.get_attribute(child, 'name')
                    arg_value = core.get_attribute(child, 'value')
                    default = core.get_attribute(child, 'default')
                    doc = core.get_attribute(child, 'doc')

                    if arg_name:
                        attributes.append(f'name="{arg_name}"')
                    if arg_value:
                        attributes.append(f'value="{arg_value}"')
                    if default:
                        attributes.append(f'default="{default}"')
                    if doc:
                        attributes.append(f'doc="{doc}"')
                    
                    attribute_string = " ".join(attributes)
                    
                    result += f"{' ' * (indent + 2)}<arg {attribute_string}/>\n"
                
                elif base_Name == "Node":
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
                        attributes.append(f'pkg="{pkg}"')
                    if node_type:
                        attributes.append(f'type="{node_type}"')
                    if args:
                        attributes.append(f'args="{args}"')
                    if respawn:
                        attributes.append(f'respawn="{respawn}"')
                    if respawn == True and respawn_delay != 0:
                        attributes.append(f'respawn_delay={respawn_delay}"')
                    if clear_params:
                        attributes.append(f'clear_params="{clear_params}"')
                    if cwd:
                        attributes.append(f'cwd="{cwd}"')
                    if launch_prefix:
                        attributes.append(f'launch-prefix="{launch_prefix}"')
                    if ns:
                        attributes.append(f'ns="{ns}"')
                    if output:
                        attributes.append(f'output="{output}"')
                    if required == False:
                        attributes.append(f'required="{required}"')
                    if machine:
                        attributes.append(f'machine="{machine}"')
                    if if_attr:
                        attributes.append(f'if="{if_attr}"')
                    if unless:
                        attributes.append(f'unless="{unless}"')
                    
                    attribute_string = " ".join(attributes)
                    
                    result += f"{' ' * (indent + 2)}<node name=\"{childName}\" {attribute_string}>\n"
                    result += xmlGenerator(child, indent + 4, topLevel = False)
                    result += f"{' ' * (indent + 2)}</node>\n"

                elif base_Name == "Remap":
                    attributes = []
                    
                    remap_from = core.get_attribute(child, 'from')
                    remap_to = core.get_attribute(child, 'to')
                        
                    if remap_from:
                        attributes.append(f'from="{remap_from}"')
                    if remap_to:
                        attributes.append(f'to="{remap_to}"')
                    
                    attribute_string = " ".join(attributes)
                        
                    result += f"{' ' * (indent + 2)}<remap {attribute_string}/>\n"
                
                elif base_Name == "Include":
                    attributes = []
                    
                    file_name = core.get_attribute(child, 'name')
                    clear_params = core.get_attribute(child, 'clear_params')
                    ns = core.get_attribute(child, "ns")
                    pass_all_args = core.get_attribute(child, "pass_all_args")
                    if_attr = core.get_attribute(child, 'if')
                    unless = core.get_attribute(child, 'unless')

                    if file_name:
                        attributes.append(f'file="{file_name}"')
                    if clear_params:
                        attributes.append(f'clear_params="{clear_params}"')
                    if ns:
                        attributes.append(f'ns="{ns}"')
                    if pass_all_args:
                        attributes.append(f'pass_all_args="{pass_all_args}"')
                    if if_attr:
                        attributes.append(f'if="{if_attr}"')
                    if unless:
                        attributes.append(f'unless="{unless}"')
                    
                    attribute_string = " ".join(attributes)
                    
                    result += f"{' ' * (indent + 2)}<include {attribute_string}>\n"
                    result += xmlGenerator(child, indent + 4, topLevel = False)          
                    result += f"{' ' * (indent + 2)}</include>\n"
                
                elif base_Name == "Group":
                    attributes = []
                    
                    ns = core.get_attribute(child, 'name')
                    clear_params = core.get_attribute(child, 'clear_params')
                    if_attr = core.get_attribute(child, 'if')
                    unless = core.get_attribute(child, 'unless')
                    
                    if ns:
                        attributes.append(f'ns="{ns}"')
                    if clear_params:
                        attributes.append(f'clear_params="{clear_params}"')
                    if if_attr:
                        attributes.append(f'if="{if_attr}"')
                    if unless:
                        attributes.append(f'unless="{unless}"')
                    
                    attribute_string = " ".join(attributes)
                    
                    result += f"{' ' * (indent + 2)}<group {attribute_string}>\n"
                    # Recursively process children of the group
                    result += xmlGenerator(child, indent + 4, topLevel = False)          
                    result += f"{' ' * (indent + 2)}</group>\n"
                
                elif base_Name == "Parameter":
                    attributes = []
                    
                    name = core.get_attribute(child, 'name')
                    command = core.get_attribute(child, 'command')
                    value = core.get_attribute(child, 'value')
                    binfile = core.get_attribute(child, 'binfile')
                    textfile = core.get_attribute(child, 'textfile')
                    type = core.get_attribute(child, 'type')
                    
                    if name:
                        attributes.append(f'name="{name}"')
                    if command:
                        attributes.append(f'command="{command}"')
                    if value:
                        attributes.append(f'value="{value}"')
                    if binfile:
                        attributes.append(f'binfile="{binfile}"')
                    if textfile:
                        attributes.append(f'textfile="{textfile}"')
                    if type:
                        attributes.append(f'type="{type}"')
                        
                    attribute_string = " ".join(attributes)
                    
                    result += f"{' ' * (indent + 2)}<param {attribute_string}/>\n"
                
                elif base_Name == "rosparam":
                    attributes = []
                    
                    name = core.get_attribute(child, 'name')
                    command = core.get_attribute(child, 'command')
                    file = core.get_attribute(child, 'file')
                    param = core.get_attribute(child, 'param')
                    ns = core.get_attribute(child, 'ns')
                    subst_value = core.get_attribute(child, 'subst_value')
                    
                    if command:
                        attributes.append(f'command="{command}"')
                    if file:
                        attributes.append(f'file="{file}"')
                    if param:
                        attributes.append(f'param="{param}"')
                    if ns:
                        attributes.append(f'ns="{ns}"')
                    if subst_value == False:
                        attributes.append(f'subst_value="{subst_value}"')
                    
                    attribute_string = " ".join(attributes)
                    
                    result += f"{' ' * (indent + 2)}<rosparam {attribute_string}>\n"
                    result += xmlGenerator(child, indent + 4, topLevel = False)
                    result += f"{' ' * (indent + 2)}</rosparam>\n"
                    
                elif base_Name == "Machine":
                    attributes = []
                    
                    name = core.get_attribute(child, 'name')
                    address = core.get_attribute(child, 'address')
                    env_loader = core.get_attribute(child, 'env-loader')
                    default = core.get_attribute(child, 'default')
                    user = core.get_attribute(child, 'user')
                    password = core.get_attribute(child, 'password')
                    timeout = core.get_attribute(child, 'timeout')
                    
                    if name:
                        attributes.append(f'name="{name}"')
                    if address:
                        attributes.append(f'address="{address}"')
                    if env_loader:
                        attributes.append(f'env-loader="{env_loader}"')
                    if default:
                        attributes.append(f'default="{default}"')
                    if user:
                        attributes.append(f'user="{user}"')
                    if password:
                        attributes.append(f'password="{password}"')
                    if timeout != 10:
                        attributes.append(f'timeout="{timeout}"')
                        
                    attribute_string = " ".join(attributes)
                        
                    result += f"{' ' * (indent + 2)}<machine {attribute_string}>\n"           
                    result += xmlGenerator(child, indent + 4,topLevel = False)
                    result += f"{' ' * (indent + 2)}</machine>\n"
                
                elif base_Name == "Env":
                    attributes = []
                    
                    name = core.get_attribute(child, 'name')
                    value = core.get_attribute(child, 'value')
                    
                    if name:
                        attributes.append(f'name="{name}"')
                    if value:
                        attributes.append(f'value="{value}"')
                        
                    attribute_string = " ".join(attributes)
                        
                    result += f"{' ' * (indent + 2)}<env {attribute_string}/>\n"     
                
                elif base_Name == "Test":
                    attributes = []
                    
                    test_name = core.get_attribute(child, 'test-name')
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
                    
                    if pkg:
                        attributes.append(f'pkg="{pkg}"')
                    if test_name:
                        attributes.append(f'test-name="{test_name}"')
                    if node_type:
                        attributes.append(f'type="{node_type}"')
                    if name:
                        attributes.append(f'name="{name}"')
                    if args:
                        attributes.append(f'args="{args}"')
                    if clear_params:
                        attributes.append(f'clear_params="{clear_params}"')    
                    if cwd:
                        attributes.append(f'cwd="{cwd}"')
                    if launch_prefix:
                        attributes.append(f'launch-prefix="{launch_prefix}"')
                    if ns:
                        attributes.append(f'ns="{ns}"')
                    if retry:
                        attributes.append(f'retry="{retry}"')
                    if time_limit != 60:
                        attributes.append(f'time-limit="{time_limit}"')    
                        
                    attribute_string = " ".join(attributes)
                    
                    result += f"{' ' * (indent + 2)}<test {attribute_string}>\n"
                    result += xmlGenerator(child, indent + 4, topLevel = False)
                    result += f"{' ' * (indent + 2)}</test>\n"
                    
                elif "rosparamBody":
                    result += textwrap.indent(core.get_attribute(child, 'body'), f"{' ' * (indent + 2)}") + "\n"
                
            if topLevel:
                result += " " * indent + "</launch>\n"
            
            return result
            
        output = xmlGenerator(active_node)
        logger.info(f"Output:\n{output}")
        
        def clean_filename(filename, replacement = "_"):
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