"""
This is where the implementation of the plugin code goes.
The MakeConnections-class is imported from both run_plugin.py and run_debug.py
"""
import sys
import logging
from webgme_bindings import PluginBase
from itertools import chain

# Setup a logger
logger = logging.getLogger('MakeConnections')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)  # By default it logs to stderr..
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class MakeConnections(PluginBase):
    def main(self):
        active_node = self.active_node
        core = self.core
        logger = self.logger
        
        launch_file = active_node
        
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
        
        publishers = []
        subscribers = []
        topics = []
        remaps = []
        groups = []
        group_pubs = []
        group_subs = []
        
        def find_types(node: dict):
            """Stores list of nodes of ecah type in model

            Args:
                node (dict): Current node
            """            
            
            meta_node = core.get_base_type(node)
            meta_type = 'undefined'
            if meta_node:
                meta_type = core.get_attribute(meta_node, 'name')
            if meta_type == "Publisher":
                publishers.append(node)
            if meta_type == "Subscriber":
                subscribers.append(node)
            if meta_type == "Topic":
                topics.append(node)
            if meta_type == "Remap":
                remaps.append(node)
            if meta_type == "Group":
                groups.append(node)
            if meta_type == "GroupPublisher":
                group_pubs.append(node)
            if meta_type == "GroupSubscriber":
                group_subs.append(node)
            
        def get_connectable_ports(node: dict) -> tuple:
            """Finds all types of publishers and subscibers in the model

            Args:
                node (dict): Node to search for ports

            Returns:
                tuple: List of publishers and list of subscribers
            """            
            
            pubs = []
            subs = []
            
            children = core.load_children(node)
            for c in children:
                grand_children = core.load_children(c)
                for g in grand_children:
                    meta_node = core.get_base_type(g)
                    meta_type = core.get_attribute(meta_node, 'name')
                    if meta_type == "Publisher" or meta_type == "GroupPublisher":
                        pubs.append(g)
                    if meta_type == "Subscriber" or meta_type == "GroupSubscriber":
                        subs.append(g)
                    
            return (pubs, subs)
        
        
        def draw_connection(pub: dict, sub: dict, name: str):
            """Adds a connection between the publisher and subscriber

            Args:
                pub (dict): Publisher node to set as source
                sub (dict): Subscriber node to set as destination
                name (str): Name of topic being communicated
            """            
            
            parent = core.get_common_parent([pub, sub])
            
            new_topic = core.create_child(parent, self.util.META(active_node)["Topic"])
            
            core.set_pointer(new_topic, 'src', pub)
            core.set_pointer(new_topic, 'dst', sub)
            core.set_attribute(new_topic, 'name', name)
            
        def count_slashes(string: dict) -> int:
            """Counts the number of slashes / in a node path of a node

            Args:
                string (dict): Node to count slashes in 

            Returns:
                int: Number of slashes in string
            """            
            
            return string["nodePath"].count('/')
        
        def remap_name(r_from: str, r_to: str, name: str) -> str:
            """Remaps the name using the specified from and to values

            Args:
                r_from (str): From in remap
                r_to (str): To in remap
                name (str): Name to be remapped

            Returns:
                str: Remapped name
            """            
            
            from_split = r_from.split("/")
            to_split = r_to.split("/")
            name_split = name.split("/")
            
            if len(from_split) <= len(name_split) and from_split == name_split[:len(from_split)]:
                new_name = to_split + name_split[len(from_split):]
                return "/".join(new_name)
            else:
                return name
        
        # Get list of publishers, subscribers, topics, group pubs, group subs    
        self.util.traverse(active_node, find_types)
        
        # Delete all existing topics, group pubs, group subs
        for t in topics:
            core.delete_node(t)
        
        include_group_pubs = []
        include_group_subs = []
        
        for p in group_pubs:
            if get_type(core.get_parent(p)) == "Group":
                core.delete_node(p)
            else:
                include_group_pubs.append(p)
        
        for s in group_subs:
            if get_type(core.get_parent(s)) == "Group":
                core.delete_node(s)
            else:
                include_group_subs.append(s)
        
        # Add new group nodes
        sorted_groups = sorted(groups, key = lambda x: -1 * count_slashes(x))
        new_group_pubs = []
        new_group_subs = []
        for g in sorted_groups:
            pubs, subs = get_connectable_ports(g)
            
            for node in chain(pubs, subs):
                meta_type = get_type(node)
            
                name = core.get_attribute(node, 'name')
                
                parent = core.get_parent(node)
                parent_name = None
                if get_type(parent) == "Node":
                    parent_name = core.get_attribute(parent, "name")
                elif get_type(parent) == "Test":
                    parent_name = core.get_attribute(parent, "testName")
                    
                g_name = core.get_attribute(g, "name")
                ns = ""
                if g_name and name[0] != "/":
                    ns = g_name + "/"
                
                if meta_type == "Publisher":
                    new_group_pub = core.create_child(g, self.util.META(active_node)["GroupPublisher"])
                    core.set_attribute(new_group_pub, 'name', ns + name)
                    core.set_attribute(new_group_pub, 'nodeName', parent_name)
                    new_group_pubs.append(new_group_pub)
                if meta_type == "Subscriber":
                    new_group_sub = core.create_child(g, self.util.META(active_node)["GroupSubscriber"])
                    core.set_attribute(new_group_sub, 'name', ns + name)
                    core.set_attribute(new_group_sub, 'nodeName', parent_name)
                    new_group_subs.append(new_group_sub)
                    
                if meta_type == "GroupPublisher" and get_type(parent) == "Include":
                    new_group_pub = core.create_child(g, self.util.META(active_node)["GroupPublisher"])
                    core.set_attribute(new_group_pub, 'name', ns + name)
                    core.set_attribute(new_group_pub, 'nodeName', core.get_attribute(node, 'nodeName'))
                    new_group_pubs.append(new_group_pub)
                if meta_type == "GroupSubscriber" and get_type(parent) == "Include":
                    new_group_sub = core.create_child(g, self.util.META(active_node)["GroupSubscriber"])
                    core.set_attribute(new_group_sub, 'name', ns + name)
                    core.set_attribute(new_group_sub, 'nodeName', core.get_attribute(node, 'nodeName'))
                    new_group_subs.append(new_group_sub)
                    
                if meta_type == "GroupPublisher" and get_type(parent) == "Group":
                    new_group_pub = core.create_child(g, self.util.META(active_node)["GroupPublisher"])
                    core.set_attribute(new_group_pub, 'name', ns + name)
                    core.set_attribute(new_group_pub, 'nodeName', core.get_attribute(node, 'nodeName'))
                    new_group_pubs.append(new_group_pub)
                if meta_type == "GroupSubscriber" and get_type(parent) == "Group":
                    new_group_sub = core.create_child(g, self.util.META(active_node)["GroupSubscriber"])
                    core.set_attribute(new_group_sub, 'name', ns + name)
                    core.set_attribute(new_group_sub, 'nodeName', core.get_attribute(node, 'nodeName'))
                    new_group_subs.append(new_group_sub)
        
        # Set up empty dictionary for pubs and subs
        pub_dict = dict()
        sub_dict = dict()
        
        # Set up publisher and subscriber dictionary before remap
        for p in chain(publishers, include_group_pubs, new_group_pubs):
            name = core.get_attribute(p, 'name')
            pub_dict[p["nodePath"]] = {"node": p, "old_name": name, "remap_name": name}
            
        for s in chain(subscribers, include_group_subs, new_group_subs):
            name = core.get_attribute(s, 'name')
            sub_dict[s["nodePath"]] = {"node": s,"old_name": name, "remap_name": name}
        
        # Apply remaps in correct order
        sorted_remaps = sorted(remaps, key=count_slashes)
        for r in reversed(sorted_remaps):
            r_parent = core.get_parent(r)

            r_from = core.get_attribute(r, 'from')
            r_to = core.get_attribute(r, 'to')
            
            def remap_fcn(node: dict):
                """Builds a dictionary containing the remap names of all publishers and subscribers

                Args:
                    node (dict): Node to traverse
                """                
                
                meta_node = core.get_base_type(node)
                meta_type = core.get_attribute(meta_node, 'name')
                if meta_type in ["Publisher", "Subscriber", "GroupPublisher", "GroupSubscriber"]:
                    if node["nodePath"] in pub_dict:
                        pub_dict[node["nodePath"]]["remap_name"] = remap_name(r_from, r_to, pub_dict[node["nodePath"]]["remap_name"])
                    if node["nodePath"] in sub_dict:
                        sub_dict[node["nodePath"]]["remap_name"] = remap_name(r_from, r_to, sub_dict[node["nodePath"]]["remap_name"])
                
            children = core.load_children(r_parent)
            for c in children:
                self.util.traverse(c, remap_fcn)
        
        # Draw connections at launch file and within each group
        for g in chain(sorted_groups, [launch_file]):
            pubs, subs = get_connectable_ports(g)
            for p in pubs:
                p_name = pub_dict[p["nodePath"]]["remap_name"]
                for s in subs:
                    s_name = sub_dict[s["nodePath"]]["remap_name"]
                    if p_name == s_name:
                        draw_connection(p, s, p_name)
        
        # Save updates
        new_commit_hash = self.util.save(core.load_root(self.project.get_root_hash(self.commit_hash)), self.commit_hash)    
        self.project.set_branch_hash(
            branch_name=self.branch_name,
            new_hash=new_commit_hash["hash"],
            old_hash=self.commit_hash
        )
        