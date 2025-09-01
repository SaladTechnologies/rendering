
import subprocess
import os
import json
import re
import time
import math


# List available devices for benchmarking and rendering
def list_devices():
        cmd = [
                "blender", "-b", "--python-expr",
                "import bpy; prefs=bpy.context.preferences.addons['cycles'].preferences; "
                "print('CPU:', [d.name for d in prefs.get_devices_for_type('CPU')], "
                "'CUDA:', [d.name for d in prefs.get_devices_for_type('CUDA') if d.type=='CUDA'], "
                "'OPTIX:', [d.name for d in prefs.get_devices_for_type('OPTIX') if d.type=='OPTIX'])"
        ]
        print(f"\nListig devices")
        print("Executing: " + ' '.join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if line.startswith("CPU:"):
                print(line)


# Download scenes and run the Blender benchmark using 'benchmark-launcher-cli'.
# https://opendata.blender.org/

# The scenes are downloaded to ~/.cache/blender-benchmark-launcher/scenes.
# https://www.blender.org/download/demo-files/#cycles
# classroom: {'resolution_x': 1920, 'resolution_y': 1080, 'percentage': 100, 'final_resolution': (1920, 1080), 'samples': 300 }
# monster:   {'resolution_x': 1024, 'resolution_y': 1024, 'percentage': 100, 'final_resolution': (1024, 1024), 'samples': 256 }
# junkshop:  {'resolution_x': 2000, 'resolution_y': 1000, 'percentage': 100, 'final_resolution': (2000, 1000), 'samples': 240 }

# The benchmark renders only a single frame per scene by default.
# The benchmark results are saved to a JSON file specified by 'output_file'.

# Example entry in the JSON results - 'junkshop', with samples of 240 in the .blend file:
# "stats": {
#     "device_peak_memory": 4787.01,
#     "number_of_samples": 97,                     # The number of samples actually rendered (may be less than the requested number if a time limit is set and reached).
#     "total_render_time": 45.8206,                # Total wall-clock time for the scene, including loading, warm-up, rendering, and final synchronization.
#     "time_for_samples": 32.797165,               # Time spent performing the actual rendering of the specified number of samples (the render loop).
#     "render_time_no_sync": 32.7977,              # Time spent in the render loop excluding GPU/CPU synchronization overhead (waiting for tiles, memory flushes, etc.).
#                                                  # Conceptually, 'render_time_no_sync' ≤ 'time_for_samples', but small deviations due to measurement precision are normal.
#     "time_limit": 30,                            # Maximum allowed time (30 seconds per scene) for the render loop ('time_for_samples'). 
#                                                  # Rendering stops early if the scene completes all samples before reaching this limit.
#                                                  # The 30-second limit is enforced by 'benchmark-launcher-cli', not by the .blend file itself.
#     "samples_per_minute": 177.45436229015527     # Final performance metric: throughput calculated only from the actual render loop ('time_for_samples'), excluding scene loading and warm-up.
# }

# The Blender OpenData Score is the sum of the samples_per_minute values for all three scenes.
# https://opendata.blender.org/about/#benchmark-score
def run_blender_benchmark(blender_version="4.5.0", device_type="CUDA", scenes=None, output_file="benchmark_results.json") -> None:
  
    if scenes is None:
        scenes = ["monster", "junkshop", "classroom"]
    
    # Step 0: List the devices which can be benchmarked
    #list_cmd = ["./benchmark-launcher-cli", "devices",  "--blender-version", blender_version] 
    #print(f"\nListig devices which can be benchmarked")
    #print("Executing: " + ' '.join(list_cmd))
    #subprocess.run(list_cmd, check=True)

    # Step 1: Download scenes
    # download_cmd = ["./benchmark-launcher-cli", "scenes", "download", "--blender-version", blender_version] + scenes
    # print(f"\nDownloading scenes: {scenes}")
    # print("Executing: " + ' '.join(download_cmd))
    # subprocess.run(download_cmd, check=True)
    
    # Step 2: Run benchmark
    benchmark_cmd = [
        "./benchmark-launcher-cli",
        "benchmark",
        "--blender-version", blender_version,
        "--device-type", device_type,
        "--json"
    ] + scenes
    print(f"\nRunning benchmark for scenes: {scenes}")
    print("Executing: " + ' '.join(benchmark_cmd))
    with open(output_file, "w") as f:
        subprocess.run(benchmark_cmd, stdout=f, check=True)
    
    print(f"\nBenchmark complete. Results saved to {output_file}")


# Compute Blender OpenData Score from the JSON results file.
# The Blender OpenData Score is the sum of the samples_per_minute values for all three scenes.
# https://opendata.blender.org/about/#benchmark-score
def compute_blender_score(json_file_path: str) -> float:
    with open(json_file_path, "r") as f:
        data = json.load(f)
    score = sum(scene["stats"]["samples_per_minute"] for scene in data)
    return score


# The scenes are downloaded to ~/.cache/blender-benchmark-launcher/scenes.
# List all scenes with a main.blend file in the cache directory.
def list_main_blend_with_folder(base_dir=None):

    if base_dir is None:
        base_dir = os.path.expanduser("~/.cache/blender-benchmark-launcher/scenes")
    
    result = []
    if not os.path.exists(base_dir):
        raise FileNotFoundError(f"Scenes folder not found: {base_dir}")
    
    # iterate over hash folders
    for hash_folder in os.listdir(base_dir):
        hash_path = os.path.join(base_dir, hash_folder)
        if not os.path.isdir(hash_path):
            continue
        
        # iterate over scene folders inside the hash folder
        for scene_name in os.listdir(hash_path):
            scene_folder = os.path.join(hash_path, scene_name)
            main_blend = os.path.join(scene_folder, "main.blend")
            if os.path.isfile(main_blend):
                result.append({
                    "folder": hash_folder,
                    "scene": scene_name,
                    "main_blend_path": main_blend
                })
    
    return result


# Extract scene settings from a .blend file using Blender's Python API.
# Returns a dictionary with keys: resolution_x, resolution_y, percentage, final_resolution, samples, time_limit
# 'time_limit' means the maximum allowed time (in seconds) for the render loop specified in the .blend file, and 0 means no time limit.
def get_blend_settings(blend_file: str):
    cmd = [
        "blender",
        "-b", blend_file,
        "--python-expr",
        (
            "import bpy; "
            "print('RES_X', bpy.context.scene.render.resolution_x); "
            "print('RES_Y', bpy.context.scene.render.resolution_y); "
            "print('RES_PCT', bpy.context.scene.render.resolution_percentage); "
            "print('SAMPLES', bpy.context.scene.cycles.samples); "
            "print('TIME_LIMIT', bpy.context.scene.cycles.time_limit)"
        ),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    out = result.stdout

    # Regex parse values
    res_x = int(re.search(r"RES_X (\d+)", out).group(1))
    res_y = int(re.search(r"RES_Y (\d+)", out).group(1))
    res_pct = int(re.search(r"RES_PCT (\d+)", out).group(1))
    samples = int(re.search(r"SAMPLES (\d+)", out).group(1))
    time_limit = int(re.search(r"TIME_LIMIT (\d+)", out).group(1))

    # Final effective resolution
    final_x = int(res_x * res_pct / 100)
    final_y = int(res_y * res_pct / 100)

    return {
        "resolution_x": res_x,
        "resolution_y": res_y,
        "percentage": res_pct,
        "final_resolution": (final_x, final_y),
        "samples": samples,
        "time_limit": time_limit
    }


# Get meaningful real-world metrics, such as the time required to render 1 frame from a typical case (scene, samples and resolution), including scene loading and any necessary pre-processing.
# All samples in the .blend file of each scene are rendered, no time limit.
# Renders NUM_RUNS times and returns geometric mean of render times. The geometric mean is used because it fairly summarizes performance across tests of varying complexity, avoiding domination by outliers and reflecting relative speed differences.
# The Open Data benchmark scenes (classroom, monster, junkshop) are static without animation, rendering multiple frames would give essentially the same result every time.
# Even though the scenes are static, slight differences in file size occur due to random sampling, floating-point variations, and tile/thread ordering during rendering.
def render_scene(scene_name, blend_file, output_dir, NUM_RUNS, cycles_device):
    times = []
    for i in range(NUM_RUNS):
        start_time = time.time()
        cmd = [
            "blender",
            "-b", blend_file,
            "-o", os.path.join(output_dir, f"frame_#####"),
            "-F", "PNG",
            "-f", "1",
            "--",
            "--cycles-device", cycles_device
        ]
        print(f"\n[{scene_name}] Run {i+1}/{NUM_RUNS}...")
        print("Executing: " + ' '.join(cmd))

        # subprocess.run(cmd, check=True)
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        elapsed = time.time() - start_time
        print(f"[{scene_name}] Run {i+1} completed in {elapsed:.2f}s")
        times.append(elapsed)

    # Return geometric mean of this scene’s runs
    geom_mean = math.prod(times) ** (1/len(times))
    print(f"[{scene_name}] Geometric Mean Render Time: {geom_mean:.2f}s")
    return geom_mean