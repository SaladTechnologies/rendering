
#!/bin/bash

echo -e "\nRunning Jupyter Lab on port 8888 ..."
jupyter lab \
  --no-browser \
  --port=8888 \
  --ip=* \
  --allow-root \
  --ServerApp.allow_origin='*' \
  --ServerApp.allow_remote_access=True \
  --NotebookApp.token='' \
  --NotebookApp.password='' \
  > /dev/null 2>&1 &

# Keep the container alive
echo -e "\nSleep infinity ..."
sleep infinity


# python3 benchmark.py