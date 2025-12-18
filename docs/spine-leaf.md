# Latency Profiling in Spine-Leaf Architecture

This document provides an overview of latency profiling in a spine-leaf network architecture. It outlines the key components, methodologies, and tools used to measure and analyze latency within this type of network topology.

![alt text](images/leaf-spine-topo.png "Spine-Leaf Topology")

## Overview of Spine-Leaf Architecture

Yaml configuration for a basic spine-leaf topology:

```yaml
topology:
  spine:
    - name: spine1
      pipeline: 3
      ports: [17, 18, 19, 20, 21, 22, 23, 24]
  leaf:
    - name: leaf1
      pipeline: 1
      ports: [1, 2, 3, 4]
      network: "10.0.1.0/24"
    - name: leaf2
      pipeline: 1
      ports: [5, 6, 7, 8]
      network: "10.0.2.0/24"
    - name: leaf3
      pipeline: 2
      ports: [9, 10, 11, 12]
      network: "10.0.3.0/24"
    - name: leaf4
      pipeline: 2
      ports: [13, 14, 15, 16]
      network: "10.0.4.0/24"
```