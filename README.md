# Rendering Workloads on SaladCloud

This repository provides resources for running rendering workloads on SaladCloud, including blogs, benchmarking code, reference designs, demo applications, and test reports

If you are new to SaladCloud, we recommend starting with [the SCE Architectural Overview](https://docs.salad.com/products/sce/getting-started/architectual-overview) and [the Docker Run on SaladCloud](https://docs.salad.com/tutorials/docker-run). The tutorials - [Build High-Performance Applications](https://docs.salad.com/tutorials/high-performance-apps) and [Build High-Performance Storage Solutions](https://docs.salad.com/tutorials/high-performance-storage-solutions) share best practices along with proven insights from customers who have successfully built large-scale AI inference applications, using tens to thousands of Salad GPU nodes.

### Blender Rendering Benchmarks

For performance and cost benchmarks of running Blender on SaladCloud, please refer to [this blog post](https://blog.salad.com/blender-rendering-benchmark/).

### Blender Benchmark Code

Please refer to [the link](https://github.com/SaladTechnologies/rendering/tree/main/blender-benchmark) for the Dockerfile and benchmark code. 

When run on SaladCloud, the workflow first executes the benchmarking code, reports the results to an AWS DynamoDB table, and then exits. The data is subsequently downloaded and analyzed using Pandas in JupyterLab.

You can run the image locally; refer to [this link](https://github.com/SaladTechnologies/rendering/blob/main/blender-benchmark/examples.txt#L33) for details.

### Blender Solution on SaladCloud

To run Blender efficiently on SaladCloud, several factors must be considered, including input data organization and migration, chunked execution, checkpoint management, job queue integration, and Flamenco cluster setup. 

See [this link](https://docs.salad.com/container-engine/how-to-guides/rendering/blender-input) for details on Blender input data organization and migration.