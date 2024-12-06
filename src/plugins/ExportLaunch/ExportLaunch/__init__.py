"""
This is where the implementation of the plugin code goes.
The ExportLaunch-class is imported from both run_plugin.py and run_debug.py
"""
import sys
import logging
from webgme_bindings import PluginBase

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
        indent=0
        active_node = self.active_node
        core = self.core
        logger = self.logger
        
        visited_nodes = []
        ignoreMetaType = ["GroupPublisher","GroupSubscriber","Subscriber","Topic","Publisher"]
        
        
        meta_types = ["LaunchFile", "Include", "Argument", "Remap", "Group", "Parameter", "rosparam", "Node", "Topic", "GroupPublisher", "GroupSubscriber", "Subscriber", "Publisher"]

        def get_type(node):
            base_type = core.get_base(node)

            if core.get_attribute(base_type, 'name') not in meta_types:
                base_type = core.get_base(base_type)

            return core.get_attribute(base_type, 'name')
        
        def xmlGenerator(activeNode,indent = 0,topLevel = True):
            result = ""
            node_path = core.get_path(activeNode)   
            
            if topLevel:
                result += " " * indent + "\n<launch>\n"
                
            if node_path in visited_nodes:
                #logger.warning(f"Node already visited, skipping: {node_path}")
                return result +'\n</launch>'
            
            visited_nodes.append(node_path)
            children = core.load_children(activeNode)
            
            for child in children:
                
                meta_type = core.get_meta_type(child)
                metaTypeName = core.get_attribute(meta_type,'name')
                childName = core.get_attribute(child,'name')
                logger.info(f"metaTypeName {metaTypeName}")
                base_Name = get_type(child)
                if base_Name in ignoreMetaType:
                    continue
                #logger.info(f"{core.get_attribute(child, 'pkg')} {core.get_attribute(child, 'type')} {core.get_attribute(child, 'args')} {core.get_attribute(child, 'name')} core.get_attribute(child, 'args')")
                if base_Name == "Argument":
                    attributes = []
                    arg_name = core.get_attribute(child, 'name')
                    arg_value = core.get_attribute(child, 'value')
                    default = core.get_attribute(child, 'default')
                    logger.info(f"{arg_name} {arg_value}")
                    attributes = []
                    if arg_name:
                        attributes.append(f'name="{arg_name}"')
                    if arg_value:
                        attributes.append(f'value="{arg_value}"')
                    if default:
                        attributes.append(f'default="{default}"')
                    attribute_string = " ".join(attributes)
                    result += f"{' ' * (indent + 2)}<arg {attribute_string}/>\n"
                    #result += f"{' ' * indent}{childName}()\n"
                
                elif base_Name == "Node":
                    #pkg = "operations"
                    attributes = []
                    pkg = core.get_attribute(child, 'pkg')
                    node_type = core.get_attribute(child, 'type')
                    args = core.get_attribute(child, 'args')
                    respawn = core.get_attribute(child, 'respawn')
                    if pkg:
                        attributes.append(f'pkg="{pkg}"')
                    if node_type:
                        attributes.append(f'type="{node_type}"')
                    if len(args)>0:
                        logger.info(f"args len {len(args)}")
                        attributes.append(f'args="{args}"')
                    if respawn:
                        attributes.append(f'respawn="{respawn}"')
                    attribute_string = " ".join(attributes)
                    result += f"{' ' * (indent + 2)}<node name=\"{childName}\" {attribute_string}>\n"
                    result += xmlGenerator(child, indent + 4,topLevel = False)
                    result += f"{' ' * (indent + 2)}</node>\n"

                elif base_Name == "Remap":
                    attributes = []
                    remap_from = core.get_attribute(child, 'from')
                    remap_to = core.get_attribute(child, 'to')
                    name = core.get_attribute(child, 'name')
                    #result += f"{' ' * (indent + 2)}<remap name = \"{name}\" from=\"{remap_from}\" to=\"{remap_to}\"/>\n"    
                    if remap_from:
                        attributes.append(f'from="{remap_from}"')
                    if remap_to:
                        attributes.append(f'to="{remap_to}"')
                        attribute_string = " ".join(attributes)
                        
                    result += f"{' ' * (indent + 2)}<remap {attribute_string}/>\n"
                
                elif base_Name == "Include":
                    attributes = []
                    file_name = core.get_attribute(child, 'name')
                    file_name = core.get_attribute(child, 'name')
                    if file_name:
                        if '.launch' not in file_name:
                            logger.info(f"{file_name}")
                            result += f"{' ' * (indent + 2)}<include file=\"{file_name}.launch\"/>\n"
                        else:
                            result += f"{' ' * (indent + 2)}<include file=\"{file_name}\"/>\n"
                
                elif base_Name == "Group":
                    attributes = []
                    ns = core.get_attribute(child, 'name')
                    result += f"{' ' * (indent + 2)}<group ns=\"{ns}\">\n"
                    # Recursively process children of the group
                    result += xmlGenerator(child, indent + 4,topLevel = False)          
                    result += f"{' ' * (indent + 2)}</group>\n"
                
                elif base_Name == "Parameter":
                    attributes = []
                    name = core.get_attribute(child, 'name')
                    command = core.get_attribute(child, 'command')
                    value = core.get_attribute(child, 'value')
                    
                    # Recursively process children of the group
                    result += xmlGenerator(child, indent + 4,topLevel = False)
                    #result += f"{' ' * (indent + 2)}</param>\n"
                    if name:
                        attributes.append(f'name="{name}"')
                    if command:
                        attributes.append(f'command="{command}"')
                    if value:
                        attributes.append(f'value="{value}"')
                    attribute_string = " ".join(attributes)
                    if attribute_string:
                        result += f"{' ' * (indent + 2)}<param {attribute_string}/>\n"
                
                elif base_Name == "rosparam":
                    attributes = []
                    name = core.get_attribute(child, 'name')
                    command = core.get_attribute(child, 'command')
                    file = core.get_attribute(child, 'file')
                    param = core.get_attribute(child, 'param')
                    #result += f"{' ' * (indent + 2)}<rosParam name=\"{name}\" command=\"{command}\" file = \"{file}\" param = \"{param}\">\n"
                    # Recursively process children of the group
                    if command:
                        attributes.append(f'command="{command}"')
                    if file:
                        attributes.append(f'file="{file}"')
                    if param:
                        attributes.append(f'param="{param}"')
                    attribute_string = " ".join(attributes)
                    if attribute_string:
                        result += f"{' ' * (indent + 2)}<rosparam {attribute_string}>\n"           
                    
                        
                    result += xmlGenerator(child, indent + 4,topLevel = False)
                    result += f"{' ' * (indent + 2)}</rosparam>\n"
                
            if topLevel:
                result += " " * indent + "</launch>\n"
            return result
            
        output = xmlGenerator(active_node)
        logger.info(f"output {output}")
        file_name = 'output.launch'
        file_hash = self.add_file(file_name, output)
        logger.info(f"Output saved to file with hash: {file_hash}")
        #artifact_name = core.get_attribute(active_node, 'name') + '_LaunchArtifact'
        #artifact = {core.get_attribute(active_node, 'name') + '.launch': output}

        # Add the artifact to the plugin
        #self.add_artifact(artifact_name, artifact)
        #logger.info(f"Launch file exported as artifact: {artifact_name}")