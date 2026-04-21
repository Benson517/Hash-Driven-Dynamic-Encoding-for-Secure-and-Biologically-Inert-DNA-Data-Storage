# Hash-Driven-Dynamic-Encoding-for-Secure-and-Biologically-Inert-DNA-Data-Storage

Repository Scope & Theoretical Boundary
This repository exclusively implements the Source Coding Module (State-Dependent Dynamic Mapping, SDDM) proposed in the manuscript. The Channel Coding Module (the concatenated RS+LDPC Forward Error Correction architecture abstracted in Section II-A) is not included in this release.

Primary Verification Targets of this Code:
Instead of channel noise tolerance, this code is provided to rigorously verify the algorithm's primary theoretical contributions:

Biochemical Constraint Satisfaction: Strict locking of GC content within the narrow 47%–55% window.
Absolute Homopolymer Suppression: Guaranteeing a maximum homopolymer run length of 
≤3
 nt via hard-constraint intervention.
Biochemical Inertness: Deterministic disruption of long-range Open Reading Frames (ORFs).
Information Density: Achieving a net information density of 1.619 bits/nt under these extreme constraints.
For end-to-end error resilience metrics, users must integrate this SDDM codec behind their own standard RS/LDPC decoding pipelines.


