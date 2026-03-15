# MODEL SPEC

## Model Tag
H0_BASELINE_LINDBLAD

## Objective
Establish disciplined baseline reproduction prior to nonlinear modification.

## Governing Equation Class
Standard GKSL master equation.

d rho dt equals minus i commutator of H and rho plus dissipators.

## State Variables
Two level system density matrix.

## Parameter Vector
T1  
Tphi  
Measurement noise level  

## Observables
Primary: T1 decay  
Secondary: Ramsey envelope  

## Required Invariants
Trace preservation  
Complete positivity  
Reduction to textbook limit  

## Reduction Limits
When nonlinear term is zero, recover standard Lindblad dynamics.

## Numerical Notes
Time step convergence required.  
Basis truncation convergence required.  
Noise model explicitly declared.

## Expected Failure Modes
Discretization artifact  
Noise mis specification  
Parameter overfit relative to observable count  

## Domain of Validity
Weak coupling regime  
Markovian bath  
No metastable configuration memory
