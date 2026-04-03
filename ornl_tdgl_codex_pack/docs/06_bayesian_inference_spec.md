# 06. Bayesian inference specification

## 6.1 Scope
v1 inference is restricted to **low-dimensional parameter recovery from synthetic data**.

Do not implement full spatial-field inversion in v1.

## 6.2 Inference targets
Start with the small parameter set

\[
\theta_{small} = (\sigma_\chi,\ell_\chi,\Gamma_\psi,A_{rf})
\]

under a fixed choice of:
- geometry,
- \(B_{dc}\),
- observation-weight functions \(w_f, w_Q\),
- calibration constants unless explicitly included.

Later v1.1 extensions may add:
- \(B_{dc}\),
- \(c_f\),
- \(c_Q\),
- \(Q^{-1}_{bg}\).

## 6.3 Priors
Use independent priors initially unless there is a strong reason otherwise.

Recommended defaults:
- \(\sigma_\chi \sim \text{HalfNormal}(0.25)\)
- \(\ell_\chi \sim \text{LogNormal}(\log 1.0, 0.5)\)
- \(\Gamma_\psi \sim \text{LogNormal}(\log 10^{-3}, 0.75)\)
- \(A_{rf} \sim \text{HalfNormal}(0.1)\)

These are nondimensional priors and should be configurable.

## 6.4 Observable choices
The inverse problem should not consume the raw field trajectory.

Use a summary vector built from:
- mean and variance of \(\Delta f/f_0\),
- mean and variance of \(Q^{-1}\),
- total event count,
- mean jump amplitude,
- median waiting time,
- fraction of time with `N_v > 0`.

Optionally include selected downsampled time-series windows later.

## 6.5 Synthetic data protocol
For each inference benchmark:
1. choose a truth parameter vector,
2. sample or construct a pinning field from the truth hyperparameters,
3. run the forward model,
4. compute reduced observables,
5. add observation noise,
6. freeze the resulting data package as the "observed" dataset,
7. store the truth vector separately.

All synthetic datasets must be reproducible from a stored seed bundle.

## 6.6 Likelihood models

### Default likelihood: Gaussian summary-statistic likelihood
Let the observed summary vector be \(y_{obs}\) and the forward map be \(G(\theta)\).

\[
y_{obs} = G(\theta) + \varepsilon, \qquad
\varepsilon \sim \mathcal{N}(0, \Sigma)
\tag{1}
\]

Then

\[
\log \pi(y_{obs}\mid \theta)
=
-\frac{1}{2}(G(\theta)-y_{obs})^T \Sigma^{-1}(G(\theta)-y_{obs})
-\frac{1}{2}\log|\Sigma| + C.
\tag{2}
\]

### Optional likelihood refinement
If event counts dominate the information content, allow a mixed likelihood:
- Gaussian for smooth summaries,
- Poisson or negative-binomial for event counts.

This is optional for v1. Keep the baseline Gaussian likelihood simple.

## 6.7 Inference algorithm ladder

### Stage I: MAP estimation
Implement:
- prior + likelihood evaluation,
- optimizer with bound handling,
- multiple starting points.

This is mandatory.

### Stage II: local uncertainty
Implement one:
- Laplace approximation around the MAP, or
- ensemble-based Gaussian approximation.

This is mandatory.

### Stage III: posterior sampling
Implement one lightweight sampler after the above works:
- random-walk Metropolis,
- adaptive Metropolis,
- delayed-acceptance MCMC if available.

This is recommended but not mandatory for the first code delivery.

## 6.8 Posterior predictive checks
Every inference run must generate:
- posterior predictive mean,
- posterior predictive intervals,
- comparison to synthetic observed summary vector,
- coverage diagnostics.

## 6.9 Identifiability workflow
Codex must implement the following steps:

1. **One-at-a-time sensitivity scan**
   Perturb each parameter while holding others fixed and track summary-statistic movement.

2. **Pairwise sensitivity map**
   Build coarse 2D grids for selected parameter pairs.

3. **Local Fisher-style heuristic**
   Approximate the Jacobian of summaries with respect to parameters and inspect rank / conditioning.

4. **Inference baseline**
   Run MAP + uncertainty on one synthetic truth case.

The workflow must emit warnings when summaries appear insensitive or strongly collinear.

## 6.10 Output contract
Every inference run must write:
- prior specification,
- truth vector if synthetic,
- observed data package,
- MAP estimate,
- covariance / local uncertainty object,
- posterior samples if run,
- posterior predictive summaries,
- diagnostics and trace plots if sampling is enabled.

## 6.11 Failure modes to detect
- optimizer converges to boundary repeatedly,
- flat likelihood,
- singular local covariance,
- posterior predictive mismatch,
- non-reproducible synthetic dataset generation.

On failure, mark the run as non-identifiable rather than silently returning a result.

## 6.12 Minimal success definition
The inference module is "good enough for proposal use" when:
- the default small parameter set is recoverable on synthetic data,
- the posterior predictive check passes,
- a figure analogous to `fig_synthetic_posterior_recovery.png` is generated.
