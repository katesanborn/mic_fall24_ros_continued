"""
This is where the implementation of the plugin code goes.
The MakeConnections-class is imported from both run_plugin.py and run_debug.py
"""
import sys
import logging
from webgme_bindings import PluginBase

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
        
        publishers = []
        subscribers = []
        topics = []
        remaps = []
        groups = []
        group_pubs = []
        group_subs = []
        
        def at_node(node):
            meta_node = core.get_base_type(node)
            name = core.get_attribute(node, 'name')
            path = core.get_path(node)
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
            
        def get_connectable_ports(node):
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
        
        
        def draw_connection(pub, sub, name):
            parent = core.get_common_parent([pub, sub])
            
            new_topic = core.create_child(parent, self.util.META(active_node)["Topic"])
            
            core.set_pointer(new_topic, 'src', pub)
            core.set_pointer(new_topic, 'dst', sub)
            core.set_attribute(new_topic, 'name', name)
            
        # Get list of publishers, subscribers, topics, group pubs, group subs    
        self.util.traverse(active_node, at_node)
        
        # Delete all existing topics, group pubs, group subs
        for t in topics:
            core.delete_node(t)
        
        for p in group_pubs:
            core.delete_node(p)
        
        for s in group_subs:
            core.delete_node(s)
        
        # Add new group nodes
        for g in groups:
            pubs_in_g = []
            subs_in_g = []
            def create_group_pub_sub(node):
                meta_node = core.get_base_type(node)
                name = core.get_attribute(node, 'name')
                path = core.get_path(node)
                meta_type = 'undefined'
                if meta_node:
                    meta_type = core.get_attribute(meta_node, 'name')
                
                parent = core.get_parent(node)
                parent_name = core.get_attribute(parent, "name")
                
                if meta_type == "Publisher":
                    new_group_pub = core.create_child(g, self.util.META(active_node)["GroupPublisher"])
                    core.set_attribute(new_group_pub, 'name', name)
                    core.set_attribute(new_group_pub, 'nodeName', parent_name)
                if meta_type == "Subscriber":
                    new_group_sub = core.create_child(g, self.util.META(active_node)["GroupSubscriber"])
                    core.set_attribute(new_group_sub, 'name', name)
                    core.set_attribute(new_group_sub, 'nodeName', parent_name)
                
            self.util.traverse(g, create_group_pub_sub)
        
        
        # Set up empty dictionary for pubs and subs
        pub_dict = dict()
        sub_dict = dict()
        
        # Set up publisher and subscriber dictionary before remap
        for p in publishers:
            name = core.get_attribute(p, 'name')
            pub_dict[p["nodePath"]] = {"node": p, "old_name": name, "remap_name": name}
            
        for s in subscribers:
            name = core.get_attribute(s, 'name')
            sub_dict[s["nodePath"]] = {"node": s,"old_name": name, "remap_name": name}
            
        def count_slashes(string):
            return string["nodePath"].count('/')
        
        # Apply remaps in correct order
        sorted_remaps = sorted(remaps, key=count_slashes)
        for r in reversed(sorted_remaps):
            r_parent = core.get_parent(r)

            r_from = core.get_attribute(r, 'from')
            r_to = core.get_attribute(r, 'to')
            
            def remap_fcn(node):
                meta_node = core.get_base_type(node)
                meta_type = core.get_attribute(meta_node, 'name')
                if meta_type == "Publisher" or meta_type == "Subscriber":
                    if node["nodePath"] in pub_dict:
                        if pub_dict[node["nodePath"]]["remap_name"] == r_from:
                            pub_dict[node["nodePath"]]["remap_name"] = r_to
                    if node["nodePath"] in sub_dict:
                        if sub_dict[node["nodePath"]]["remap_name"] == r_from:
                            sub_dict[node["nodePath"]]["remap_name"] = r_to
                
            children = core.load_children(r_parent)
            for c in children:
                self.util.traverse(c, remap_fcn)
            
        logger.info(f"pub dict: {pub_dict}")
        logger.info(f"sub dict: {sub_dict}")
        
        # Draw new topic connections
        def connect_at_node(node):
            meta_node = core.get_base_type(node)
            meta_type = core.get_attribute(meta_node, 'name')
            if not(meta_type == "LaunchFile" or meta_type == "Group"):
                return
            
            pubs, subs = get_connectable_ports(node)
            
            for p in pubs:
                p_topic = None
                p_meta = core.get_base_type(p)
                p_type = core.get_attribute(p_meta, 'name')
                
                if p_type == "Publisher":
                    p_topic = pub_dict[p["nodePath"]]["remap_name"]
                if p_type == "GroupPublisher":
                    for nodePath, names in pub_dict.items():
                        orig_pub = names["node"]
                        parent = core.get_parent(orig_pub)
                        if names["old_name"] == core.get_attribute(p, "name") and core.get_attribute(parent, "name") == core.get_attribute(p, "nodeName"):
                            p_topic = names["remap_name"]
                
                for s in subs:
                    s_topic = None
                    s_meta = core.get_base_type(s)
                    s_type = core.get_attribute(s_meta, 'name')
                    
                    if s_type == "Subscriber":
                        s_topic = sub_dict[s["nodePath"]]["remap_name"]
                    if s_type == "GroupSubscriber":
                        for nodePath, names in sub_dict.items():
                            orig_sub = names["node"]
                            parent = core.get_parent(orig_sub)
                            if names["old_name"] == core.get_attribute(s, "name") and core.get_attribute(parent, "name") == core.get_attribute(s, "nodeName"):
                                s_topic = names["remap_name"]
                                
                    p_path_length = count_slashes(p)
                    s_path_length = count_slashes(s)
                
                    common_parent = core.get_common_parent([p, s])
                    parent_length = count_slashes(common_parent)
                
                    if p_topic == s_topic and p_path_length == s_path_length and parent_length + 2 == p_path_length:
                        draw_connection(p, s, p_topic)
                
        self.util.traverse(active_node, connect_at_node)
        
        # Save updates
        new_commit_hash = self.util.save(core.load_root(self.project.get_root_hash(self.commit_hash)), self.commit_hash)    
        self.project.set_branch_hash(
            branch_name=self.branch_name,
            new_hash=new_commit_hash["hash"],
            old_hash=self.commit_hash
        )
        
        logger.info("DONE")
        