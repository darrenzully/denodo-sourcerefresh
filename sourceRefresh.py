import os
import re
import argparse
from typing import Tuple
import logging

import utils as util
 
PATTERN_CREATE_WRAPPER = r'CREATE OR REPLACE WRAPPER\s+(\"[^\"]*[^\"]*\"|\S*\S*)\s+(\"[^\"]*[^\"]*\"|\S*\S*)\s+[\s\S][\s\S]*?;+'
PATTERN_CREATE_TABLE = r'CREATE OR REPLACE TABLE\s+(\"[^\"]*[^\"]*\"|\S*\S*)\s+(\"[^\"]*[^\"]*\"|\S*\S*)\s+[\s\S][\s\S]*?;+'
PATTERN_ADD_SEARCH = r'ADD SEARCHMETHOD\s+(\"[^\"]*[^\"]*\"|\S*\S*)*?\(+'
PATTERN_WRAPPER = r'WRAPPER\s+\((\"[^\"]*[^\"]*\"|\S*\S*)\s+(\"[^\"]*[^\"]*\"|\S*\S*)*?\)+'
 
parser = argparse.ArgumentParser(description='''Replace variable names in renamed elements''')
parser.add_argument('-d', '--domain', help='The domain name.')
parser.add_argument('-p', '--path', help='Path to the vdb.')
args = parser.parse_args()
 
domain_name = args.domain
repo_root = args.path
slashes = len(repo_root.split('\\\\'))-1
 

def update_wrapper_in_vql(data: str, file_name: str, original_changed: bool) -> Tuple[str, bool] :
    changed = False
    var_name_to_compare = get_element_name(file_name)

    pattern_create_wrapper = re.compile(PATTERN_CREATE_WRAPPER)
    wrapper_name = re.search(pattern_create_wrapper, data)
    if wrapper_name:
        wrapper_name = wrapper_name.group(2)

    pattern_create_table = re.compile(PATTERN_CREATE_TABLE)
    baseview_name = re.search(pattern_create_table, data)
    if baseview_name:
        baseview_name = baseview_name.group(1)

    pattern_add_search = re.compile(PATTERN_ADD_SEARCH)
    add_search = re.search(pattern_add_search, data)
    if add_search:
        add_search = add_search.group(1)

    pattern_wrapper = re.compile(PATTERN_WRAPPER)
    wrapper_name_ref = re.search(pattern_wrapper, data)
    if wrapper_name_ref:
        wrapper_name_ref = wrapper_name_ref.group(2)

    if baseview_name and baseview_name != var_name_to_compare:
        changed = True
        data = data.replace(baseview_name, var_name_to_compare)
        logging.debug(f"\nFilename: \"{file_name}\"\n\t-Base View: {baseview_name} to: \"{var_name_to_compare}\"")

    if wrapper_name and wrapper_name != var_name_to_compare:
        changed = True
        data = data.replace(wrapper_name, var_name_to_compare)
        logging.debug(f"\nFilename: \"{file_name}\"\n\t-Wrapper: {wrapper_name} to: \"{var_name_to_compare}\"")

    if add_search and add_search != var_name_to_compare:
        changed = True
        data = data.replace(add_search, var_name_to_compare)
        logging.debug(f"\nFilename: \"{file_name}\"\n\t-Add Search: {add_search} to: \"{var_name_to_compare}\"")

    if wrapper_name_ref and wrapper_name_ref != var_name_to_compare:
        changed = True
        data = data.replace(wrapper_name_ref, var_name_to_compare)
        logging.debug(f"\nFilename: \"{file_name}\"\n\t-Ref Wrapper: {wrapper_name_ref} to: \"{var_name_to_compare}\"")

    return data, original_changed or changed
 
def get_element_name(vql_file: str) -> str:
    result = vql_file.replace("\\", ".").replace("/", ".").lower().split(".vql")[0]
    result = result.rsplit('.', 1)[1]
    return result
 
if not os.path.exists(repo_root):
    logging.error("ERROR: path provided does not exists!!!")

for search_dir in repo_root:
    properties_file_list = util.search_current_directory(f"*.properties", "f", True, True, None, search_dir)
    for property_file in properties_file_list:
        lines = []
        dict_prop = {}
        with open(property_file, 'r+') as f:
            for line in f:
                file_name = property_file[repo_root.__len__()+1-slashes:]
 
                if ".default" in file_name:
                    file_name = file_name.replace("\\", ".").replace("/", ".").lower().split(".default")[0]
                if ".development" in file_name:
                    file_name = file_name.replace("\\", ".").replace("/", ".").lower().split(".development")[0]
 
                (key, val) = line.split("=", 1)
                var_name_list = key.replace("\ ", " ").rsplit('.', 1)
                var_path = var_name_list[0]
                var_name = var_name_list[1]
                if var_name_list[1] == "ENCRYPTED":
                    var_name_list_2 = var_path.rsplit('.', 1)
                    var_path = var_name_list_2[0]
                    var_name = f"{var_name_list_2[1]}.{var_name}"
 
                uses_jdbc = False
                if ".jdbc" in var_path:
                    var_path = var_path.replace('.jdbc', "")
                    uses_jdbc = True
 
                if not file_name == var_path:
                    original_var_name_list = key.replace("\ ", " ").rsplit('.', 1)
                    original_var_path = original_var_name_list[0]
                    original_var_name = original_var_name_list[1]
                    if original_var_name_list[1] == "ENCRYPTED":
                        original_var_name_list_2 = original_var_path.rsplit('.', 1)[0]
                        original_var_path = original_var_name_list_2[0]
                        original_var_name = f"{original_var_name_list_2[1]}.{original_var_name}"
 
                    original_file_name = file_name.replace(" ", "\\ ")
 
                    if uses_jdbc:
                        ofn_split = original_file_name.rsplit('.', 1)
                        original_file_name = ofn_split[0] + ".jdbc." + ofn_split[1]
 
                    new_var_name = f"{original_file_name}.{var_name}"
                    old_var_name = f"{original_var_path}.{original_var_name}"
                    lines.append(f"{new_var_name}={val}")
 
                    if ".default" in property_file:
                        dict_prop[old_var_name] = new_var_name.replace("\\ ", " ")
                   
                    logging.debug(f"\nFilename: \"{property_file}\"\n\t-Variable: \"{old_var_name}\"\n\t-Fixed: \"{new_var_name}\"")
       
        if len(lines) > 0:
            with open(property_file, 'w') as f:
                f.seek(0)
                f.truncate()
                for line in lines:
                    f.write(line)
 
        if ".default" in property_file:    
            vql_file_path = property_file.replace("/", "\\").replace("\\", "\\\\").split(".default")[0]
            vql_file_name = f"{vql_file_path}.vql"
           
            changed = False
            with open(vql_file_name, 'r') as f:
                data = f.read()
 
                for (key, val) in dict_prop.items():
                    changed = True
                    data = re.sub(r'${' + key, r'${' + val, data)
                    logging.debug(f"\nFilename: \"{vql_file_name}\"\n\t-Variable: \"{key}\"\n\t-Fixed: \"{val}\"")
 
                data, changed = update_wrapper_in_vql(data, vql_file_name, changed)
 
            if changed:
                with open(vql_file_name, 'w') as f:
                    f.write(data)
 
vql_file_list = util.search_current_directory(f"*.vql", "f", True, True, None, repo_root)
for vql_file in vql_file_list:
 
    changed = False
    with open(vql_file, 'r') as f:
        data = f.read()
        if "CREATE OR REPLACE DATASOURCE" in data:
            data, changed = update_wrapper_in_vql(data, vql_file, changed)
 
    if changed:
        with open(vql_file, 'w') as f:
            f.write(data)
