import subprocess

def find_files(name, file_type, recursive=True, include_current_dir=True, exclude_path=None, search_dir=None):
    cmd = "find"
    if search_dir:
        cmd += f" '{search_dir}'"
    if not include_current_dir:
        cmd += " -mindepth 2" if file_type == "f" else " -mindepth 1"
    if not recursive:
        cmd += " -maxdepth 1"
    if file_type:
        cmd += f" -type {file_type}"
    if name:
        cmd += f" -name '{name}'"
    if exclude_path:
        cmd += f" -not -path '{exclude_path}'"
    process = run_command(cmd)
    files = byte_to_array(process.stdout or "")
    return files

def run_command(cmd, ignore_errors=False, cwd=None):
    print(f"Running command: [{cmd}]")
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=cwd)
    stdout, stderr = process.communicate()

    if stdout:
        print(f"STDOUT: {stdout}")
    if stderr:
        print(f"STDERR: {stderr}")
    
    if not ignore_errors and process.returncode != 0:
        raise Exception(f"Process ended with error. Code [{process.returncode}] STDERR: [{stderr}]")
    
    return process.returncode

def byte_to_array(stream):
    string = stream.decode("utf-8") if isinstance(stream, bytes) else stream
    arr = string.split('\n')[:-1]  # Remove the last empty element caused by the split
    return arr
