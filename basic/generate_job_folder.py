import os
import shutil
import subprocess
import json


# input:   r2:transcripts/rendering/classroom/main.blend

# output:  local_classroom/main.blend and all dependencies 
#          (including subfolders and files actually used)

# Assumption and Requirements:
'''
Dependencies are stored using relative paths.
The .blend files may link to other .blend files to reuse assets, and multiple .blend files can share the same dependencies; however, no reference files should be located outside the folder containing the main .blend files.
Don't download the same files repeatedly.
Files in the folder that are not used by the job should not be downloaded.
'''

# -----------------------------
# Configuration
# -----------------------------
BUCKET_NAME = "transcripts"
PREFIX_NAME = "rendering"
FOLDER_NAME = "classroom"
BLEND_FILE = "main.blend"

LOCAL_FOLDER = "local_classroom"

REMOTE_PATH = f"r2:{BUCKET_NAME}/{PREFIX_NAME}/{FOLDER_NAME}"

# -----------------------------
# Step 1: Empty local folder
# -----------------------------
if os.path.exists(LOCAL_FOLDER):
    shutil.rmtree(LOCAL_FOLDER)
os.makedirs(LOCAL_FOLDER, exist_ok=True)

# -----------------------------
# Step 2: Blender script to list dependencies for a .blend file
# -----------------------------
BLENDER_SCRIPT = "list_deps.py"
with open(BLENDER_SCRIPT, "w") as f:
    f.write(r"""
import bpy
import os

blend_file = bpy.data.filepath
dependencies = set() # controlled by code, not including Info, Warning and others

# 1. Linked .blend libraries
for lib in bpy.data.libraries:
    if lib.filepath:
        dependencies.add(bpy.path.abspath(lib.filepath))

# 2. Images / textures (ignore packed)
for img in bpy.data.images:
    if img.filepath and not img.packed_file:
        dependencies.add(bpy.path.abspath(img.filepath))

# 3. Audio / sounds
for snd in bpy.data.sounds:
    if snd.filepath:
        dependencies.add(bpy.path.abspath(snd.filepath))

# 4. Fonts
for fnt in bpy.data.fonts:
    if fnt.filepath:
        dependencies.add(bpy.path.abspath(fnt.filepath))

# 5. Movie clips / videos
for mov in bpy.data.movieclips:
    if mov.filepath:
        dependencies.add(bpy.path.abspath(mov.filepath))

# 6. Cache files (physics / simulations)
for cache in bpy.data.cache_files:
    if cache.filepath:
        dependencies.add(bpy.path.abspath(cache.filepath))

# all dependencies use absolute paths, based on the parsed .blend file
            
# dependencies -> rel_paths
# Convert and get the relative paths, based the parsed .blend file
cwd = os.path.dirname(blend_file)
rel_paths = set() 
for dep in dependencies:
    if dep:
        rel_path = os.path.relpath(dep, cwd)
        rel_paths.add(rel_path.replace("\\", "/"))
                        
# Print sorted list with DEP with the prefix for each extraction     
for p in sorted(rel_paths):
    print(f"DEP:{p}")
""")

# -----------------------------
# Step 3: Function to extract dependencies
# -----------------------------
def get_dependencies(blend_path, local_folder):
    """
    Extract dependencies from a Blender file using list_deps.py.
    Returns paths relative to local_folder.
    """
    cmd = ["blender", "-b", blend_path, "--python", BLENDER_SCRIPT]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
 

    deps = set()
    blend_dir = os.path.dirname(blend_path)

    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or not line.startswith("DEP:"):
            continue


        # blend_path，the parsed .blend file
        # local_folder/assets/wallClock/wallClock.blend
        # print()
        # print(local_folder)
        # print(blend_path)

        # dep_path，relative to blend_path
        # ../__ENV/Garage/Garage.hdr
        # textures/wallClock.png
        dep_path = line[len("DEP:"):].strip()
        # print(dep_path)

        # absolute path, based on local_folder
        real_path = os.path.normpath(os.path.join(blend_dir, dep_path))
        # print(real_path) 
        
        # relative path, basedon local_folder
        rel_path = os.path.relpath(real_path, local_folder).replace("\\", "/")
        # print(rel_path) 

        deps.add(rel_path)

    return deps

# -----------------------------
# Step 4-6: Recursively download .blend files and collect dependencies
# -----------------------------
to_process = [BLEND_FILE]        # queue of .blend files to process
processed_blends = set()         # already processed .blend files
all_deps_without_blends = set()  # non .blend dependencies
#all_blends = set()              # all .blend files discovered, 

while to_process:

    blend = to_process.pop()     # take a job
    if blend in processed_blends:
        continue

    processed_blends.add(blend)
    #all_blends.add(blend)

    # Download the .blend file
    local_blend_path = os.path.join(LOCAL_FOLDER, blend)
    if not os.path.exists(local_blend_path): # if the file doesn't exist
        os.makedirs(os.path.dirname(local_blend_path), exist_ok=True) # Create the missing directories in the path
        print(f"Downloading {blend}")
        # if the source path contains empty directories, rclone will create the same empty directories locally.
        subprocess.run([ "rclone", "copy", f"{REMOTE_PATH}/{blend}", os.path.dirname(local_blend_path), "--create-empty-src-dirs"], check=True)

    # Parse the .blend file
    try:
        deps = get_dependencies(local_blend_path, LOCAL_FOLDER)
    except subprocess.CalledProcessError:
        print(f"Warning: Blender failed to parse {blend}. Skipping.")
        continue

    for dep in deps:
        if dep.endswith(".blend"):
            # schedule library .blend for download and parsing
            if dep not in processed_blends:
                to_process.append(dep)
        else:
            # add non-.blend asset to download list
            all_deps_without_blends.add(dep)


# -----------------------------
# Step 7: Download all non-.blend dependencies
# Can be done concurrently
# -----------------------------
for dep in sorted(all_deps_without_blends):
    local_file = os.path.join(LOCAL_FOLDER, dep)
    os.makedirs(os.path.dirname(local_file), exist_ok=True)
    print(f"Downloading {dep}")
    subprocess.run([ "rclone", "copy", f"{REMOTE_PATH}/{dep}", os.path.dirname(local_file), "--create-empty-src-dirs"], check=True)


print("All .blend files and dependencies downloaded.")
print("Number of .blend files: ", len(processed_blends))
print(json.dumps(list(processed_blends), indent=2))
print("Number of asset files: ", len(all_deps_without_blends))
print(json.dumps(list(all_deps_without_blends), indent=2))
