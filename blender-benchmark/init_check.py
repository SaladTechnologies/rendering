import os
import time
import subprocess
import sys
import requests
from pythonping import ping
import speedtest
from dotenv import load_dotenv
load_dotenv()


SALAD_MACHINE_ID =  os.getenv("SALAD_MACHINE_ID","local") 
g_DLSPEED = int(os.getenv("DLSPEED", "50")) # Mbps
g_ULSPEED = int(os.getenv("ULSPEED", "20")) # Mbps
g_RTT     = int(os.getenv("RTT","499"))     # ms


# Test network bandwdith
def network_test():
    print("Test the network speed ....................", flush=True)
    try:
        speed_test = speedtest.Speedtest()
        bserver    = speed_test.get_best_server()
        dlspeed    = int(speed_test.download() / (1000 * 1000))  # Convert to Mbps, not Mib
        ulspeed    = int(speed_test.upload() / (1000 * 1000))  # Convert to Mbps, not Mib
        latency    = bserver['latency'] # the RTT to the selected test server
        country    = bserver['country'] 
        location   = bserver['name']
    except Exception as e:  
        # Some ISPs may block speed test traffic; in such cases, we fall back to the default network performance for the node.
        return "none", "none", g_RTT, g_DLSPEED, g_ULSPEED

    return country, location, latency, dlspeed, ulspeed


# Test network latency
# Only the root user can run this code - no issue in containers
def ping_test(tCount=10):
    if tCount ==0:
        return g_RTT, g_RTT, g_RTT
    try:
        print("To: ec2.us-west-1.amazonaws.com")
        temp = ping('ec2.us-west-1.amazonaws.com', interval=1, count=tCount, verbose=True)
        latency_uswest1 = temp.rtt_avg_ms # average of successful pings only     
    
        print("To: ec2.us-east-2.amazonaws.com")
        temp = ping('ec2.us-east-2.amazonaws.com', interval=1, count=tCount, verbose=True)
        latency_useast2 = temp.rtt_avg_ms # average of successful pings only     

        print("To: ec2.eu-central-1.amazonaws.com")  
        temp = ping('ec2.eu-central-1.amazonaws.com', interval=1, count=tCount,verbose=True)
        latency_eucentral1 = temp.rtt_avg_ms # average of successful pings only.
    except Exception as e:  
        return g_RTT, g_RTT, g_RTT
    
    return latency_uswest1, latency_useast2, latency_eucentral1


# Read the supported CUDA RT Version
def Get_CUDA_Version():
    try:
        cmd = 'nvidia-smi'
        output = subprocess.check_output(cmd, shell=True, text=True)
        output = output.split("\n")[2]
        output = output.split("CUDA Version: ")[-1]
        version = float(output.split(" ")[0])
    except Exception as e: 
        return 0
    return version 


# Get the GPU info
def Get_GPUs():
    try:
        cmd = ('nvidia-smi --query-gpu=gpu_name,memory.total,memory.used,memory.free,'
               'utilization.memory,temperature.gpu,utilization.gpu --format=csv,noheader,nounits')
        output = subprocess.check_output(cmd, shell=True, text=True)
        lines = output.strip().split('\n')
        for line in lines: # 1 and 8 ( few 2 )
            gpu_name, vram_total, vram_used, vram_free, mem_util, temp, gpu_util = line.strip().split(', ')
            result = {
                'gpu_number': len(lines),
                'gpu_type': gpu_name,
                'vram_total': int(vram_total),
                'vram_used': int(vram_used),
                'vram_free': int(vram_free),
                'vram_utilization': int(mem_util),
                'gpu_temperature': int(temp),
                'gpu_utilization': int(gpu_util)
            }
            break
        return result
    except Exception as e:
        return {}


def Initial_Check():    

    if SALAD_MACHINE_ID == "LOCAL" or SALAD_MACHINE_ID == "local":       # Skip the initial checks if run locally    
        environment= { "pass": str(True) }   
    else:
        # Network test: bandwidth
        country, location, latency, dlspeed, ulspeed = network_test() 
        print(f"Networt: {country}, {location}, DL {dlspeed} Mbps, UL {ulspeed} Mbps")
    
        # Network test: latency to some locations; should reallocate if ping fails
        latency_us_w, latency_us_e, latency_eu = ping_test(tCount = 10) 
        print(f"Latency: to US West {latency_us_w} ms, to US East {latency_us_e} ms, to EU Central {latency_eu} ms")

        if ulspeed < g_ULSPEED or dlspeed < g_DLSPEED or latency_us_w > g_RTT or latency_us_e > g_RTT or latency_eu > g_RTT:
            Pass = False
        else:
            Pass = True

        # CUDA Version
        CUDA_version = Get_CUDA_Version()
        print("CUDA Version:", CUDA_version)

        # GPU Info
        GPUS = Get_GPUs()
        print("GPU Info:", GPUS)

        environment = { "salad_machine_id":   SALAD_MACHINE_ID,
                        "pass":               str(Pass),
                        "country":            country,
                        "location":           location,
                        "rtt_ms":             str(latency),
                        "upload_Mbps":        str(ulspeed),
                        "download_Mbps":      str(dlspeed), 
                        "rtt_to_us_west1_ms": str(latency_us_w),                        
                        "rtt_to_us_east2_ms": str(latency_us_e),
                        "rtt_to_eu_cent1_ms": str(latency_eu),
                        "cuda_version":       CUDA_version,
                        } | GPUS

    return environment


# Trigger node reallocation if a node is not suitable
# https://docs.salad.com/products/sce/container-groups/imds/imds-reallocate
def Reallocate(reason):
    local_run = True if 'local' in SALAD_MACHINE_ID.lower() else False
    
    print(reason)

    if (local_run):  # Run locally
        print("Call the exitl to restart ......", flush=True) 
        os.execl(sys.executable, sys.executable, *sys.argv)
    else:            # Run on SaladCloud
        print("Call the IMDS reallocate ......", flush=True)
        url = "http://169.254.169.254/v1/reallocate"
        headers = {'Content-Type': 'application/json',
                   'Metadata': 'true'}
        body = {"Reason": reason}
        _ = requests.post(url, headers=headers, json=body)
        time.sleep(10)

