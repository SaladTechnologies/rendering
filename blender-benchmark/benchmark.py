import shutil
import os
import json
import math
import requests
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from init_check import Initial_Check, Reallocate
from helper import list_devices, run_blender_benchmark, \
                   compute_blender_score, \
                   list_main_blend_with_folder, \
                   get_blend_settings, \
                   render_scene


OUTPUT_FILE_CUDA = "benchmark_results_cuda.json" # CUDA, the original benchmark results file from 'benchmark-launcher-cli'.
OUTPUT_FILE_CPU  = "benchmark_results_cpu.json"  # CPU, the original benchmark results file from 'benchmark-launcher-cli'.
NUM_RUNS = 1 # Number of runs per scene
DEVICE =  os.getenv("DEVICE","CUDA") # Custom Benchmark: "CUDA" or "CPU" ( "OPTIX" is not supported)


# Access to the Job Reporting System
benchmark_url = os.getenv("REPORTING_API_URL", "")
benchmark_id = os.getenv("BENCHMARK_ID", "")   # Test Records
benchmark_sl_id = benchmark_id + "-sl"         # Error messages
benchmark_auth_header = os.getenv("REPORTING_AUTH_HEADER", "")
benchmark_auth_value = os.getenv("REPORTING_API_KEY", "")
benchmark_headers = { benchmark_auth_header: benchmark_auth_value }


g_Start = time.perf_counter()


# To keep the final results for report and analysis
g_Result = Initial_Check()


try: 
    # List devices ("CPU", "OPTIX", "CUDA")
    # list_devices()

    # Warm up only
    # If PTX needs to be compiled dynamically, the first benchmark will be slower.
    print("\n" + 60 * "-" + " Warming up...")
    run_blender_benchmark(output_file=OUTPUT_FILE_CUDA, device_type="CUDA")

    # Run the Blender benchmark using 'benchmark-launcher-cli': CPU and CUDA   
    # https://opendata.blender.org/
    print("\n" + 60 * "-" + " Start standard benchmarking ...")
    run_blender_benchmark(output_file=OUTPUT_FILE_CPU,  device_type="CPU")
    run_blender_benchmark(output_file=OUTPUT_FILE_CUDA, device_type="CUDA") # Override the previous results

except Exception as e:
    g_End = time.perf_counter()
    g_Result['test_time'] = "{:.3f}".format(g_End - g_Start)  
    g_Result['error'] = f"An error occurred: {e}"
    print(g_Result)
    if benchmark_url != "":
        requests.post( f"{benchmark_url}/{benchmark_sl_id}",json=g_Result, headers=benchmark_headers)
    Reallocate(e)


try: 
    # Compute the Blender OpenData Score from the JSON results file, which is the sum of the samples_per_minute values for all three scenes.
    # https://opendata.blender.org/about/#benchmark-score
    temp = compute_blender_score(json_file_path=OUTPUT_FILE_CUDA)
    print(f"Standard Blender OpenData Score - CUDA: {temp:.2f}")
    g_Result["standard_blender_opendata_score_cuda"] = temp

    temp = compute_blender_score(json_file_path=OUTPUT_FILE_CPU)
    print(f"Standard Blender OpenData Score - CPU: {temp:.2f}")
    g_Result["standard_blender_opendata_score_cpu"] = temp

except Exception as e:
    g_End = time.perf_counter()
    g_Result['test_time'] = "{:.3f}".format(g_End - g_Start)  
    g_Result['error'] = f"An error occurred: {e}"
    print(g_Result)
    if benchmark_url != "":
        requests.post( f"{benchmark_url}/{benchmark_sl_id}",json=g_Result, headers=benchmark_headers)
    Reallocate(e)


try: 
    # Get meaningful real-world metrics from a typical case (scene, samples and resolution), including scene loading and any necessary pre-processing.
    # - the samples per min
    # - the time required to render 1st frame

    scenes = list_main_blend_with_folder() # Get all scenes with a main.blend file in the cache directory.
    print(f"\nFound {len(scenes)} scenes with main.blend")

    g_Result['custom_benchmark_device'] = DEVICE
    print(f"\nCustom Benchmark Device: {DEVICE}")

    print("\n" + 60 * "-" + " Start custom benchmarking ...")

    total_blender_score = 0
    time_list = []
    samples_per_minute_list = []

    for single_scene in scenes: # for each scene
        scene_name, blend_file, output_dir = single_scene['scene'], single_scene['main_blend_path'], f"output/{single_scene['scene']}"
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        os.makedirs(output_dir, exist_ok=True)

        temp1 = get_blend_settings(single_scene['main_blend_path']) # Extract scene settings from the .blend file.
        temp2 = render_scene(scene_name, blend_file, output_dir, NUM_RUNS, DEVICE) # Render scene and return geometric mean of render times.
        
        samples_per_minute  = temp1["samples"] * 60 / temp2

        g_Result[scene_name + '_settings'] = f"{temp1['final_resolution'][0]}x{temp1['final_resolution'][1]}*{temp1['samples']}"

        g_Result[scene_name + '_time_s_per_frame'] = temp2
        time_list.append(temp2)

        g_Result[scene_name + '_samples_per_min' ] = samples_per_minute 
        samples_per_minute_list.append(samples_per_minute)

        total_blender_score += samples_per_minute

    geom_mean_time = math.prod(time_list) ** (1 / len(time_list))
    print(f"\nGeometric Mean Time(second) per frame: {geom_mean_time:.2f}")
    g_Result['geometric_mean_time_s_per_frame'] = geom_mean_time 

    geom_mean_sample = math.prod(samples_per_minute_list) ** (1 / len(samples_per_minute_list))
    print(f"\nGeometric Mean Samples per min: {geom_mean_sample:.2f}")
    g_Result['geometric_mean_samples_per_min'] = geom_mean_sample

    # Calculate Blender OpenData Score including scene loading and any necessary pre-processing.
    print(f"\nCustom Blender OpenData Score: {total_blender_score:.2f}")
    g_Result["custom_blender_opendata_score"] = total_blender_score

except Exception as e:
    g_End = time.perf_counter()
    g_Result['test_time'] = "{:.3f}".format(g_End - g_Start)  
    g_Result['error'] = f"An error occurred: {e}"
    print(g_Result)
    if benchmark_url != "":
        requests.post( f"{benchmark_url}/{benchmark_sl_id}",json=g_Result, headers=benchmark_headers)
    Reallocate(e)


g_End = time.perf_counter()
g_Result['test_duration_s']  = "{:.3f}".format(g_End - g_Start)  
g_Result['timestamp_pdt'] = datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M:%S")


print()
print(60 * '-' + " The final result:")
print(json.dumps(g_Result, indent=4))
if benchmark_url != "":
    requests.post( f"{benchmark_url}/{benchmark_id}",json=g_Result,headers=benchmark_headers)
print(60 * '-' + " The end")

Reallocate("Changing nodes for test")