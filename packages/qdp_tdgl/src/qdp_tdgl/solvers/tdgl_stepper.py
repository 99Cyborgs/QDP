"""IMEX time stepping for deterministic TDGL evolution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from qdp_tdgl.config.models import TDGLRFCaseConfig
from qdp_tdgl.fields.currents import CurrentField
from qdp_tdgl.exceptions import SolverDivergenceError
from qdp_tdgl.fields.currents import compute_normal_current, compute_supercurrent
from qdp_tdgl.fields.forcing import VectorPotential, evaluate_forcing
from qdp_tdgl.fields.linkvars import LinkVariables, build_link_variables
from qdp_tdgl.geometry.masks import GeometryMask, StructuredGrid2D
from qdp_tdgl.solvers.linear_ops import ActiveCellMap, build_active_psi_operator
from qdp_tdgl.solvers.phi_solver import ScalarPotentialSolver
from qdp_tdgl.solvers.scipy_backend import LinearSolveResult, SciPyLinearBackend
from qdp_tdgl.solvers.state import SimulationState


@dataclass(frozen=True)
class TDGLStepContext:
    """Intermediate fields assembled for one IMEX step."""

    links: LinkVariables
    supercurrent: CurrentField
    phi: np.ndarray
    A: VectorPotential
    A_dot: VectorPotential
    phi_iterations: int
    phi_residual_norm: float
    phi_solver_method: str


class TDGLStepper:
    """Deterministic phase-1 IMEX TDGL stepper.

    The stepper treats the nonlinear reaction term and scalar-potential coupling explicitly while
    the covariant diffusion operator stays implicit on the active-cell subspace.
    """

    def __init__(
        self,
        grid: StructuredGrid2D,
        mask: GeometryMask,
        alpha: np.ndarray,
        config: TDGLRFCaseConfig,
        config_dir: Path,
    ) -> None:
        if config.solver.backend != "scipy":
            raise SolverDivergenceError("phase-1 runtime currently supports the scipy backend only")
        self.grid = grid
        self.mask = mask
        self.alpha = alpha
        self.config = config
        self.config_dir = config_dir
        self.backend = SciPyLinearBackend()
        self.active_cells = ActiveCellMap.from_mask(mask)
        self.phi_solver = ScalarPotentialSolver(
            grid=grid,
            mask=mask,
            sigma_n=config.physics.sigma_n,
            backend=self.backend,
        )

    def _build_step_context(self, psi: np.ndarray, t: float) -> TDGLStepContext:
        """Assemble forcing, links, supercurrent, and scalar potential for one step."""

        a, a_dot = evaluate_forcing(self.grid, self.config.forcing, t, config_dir=self.config_dir)
        links = build_link_variables(self.grid, a)
        supercurrent = compute_supercurrent(self.grid, self.mask, psi, links)
        phi, phi_stats = self.phi_solver.solve(
            supercurrent=supercurrent,
            a_dot=a_dot,
            linear_solver=self.config.solver.phi_linear_solver,
            rtol=self.config.solver.rtol,
            atol=self.config.solver.atol,
            max_it=self.config.solver.max_it,
        )
        return TDGLStepContext(
            links=links,
            supercurrent=supercurrent,
            phi=phi,
            A=a,
            A_dot=a_dot,
            phi_iterations=phi_stats.iterations,
            phi_residual_norm=phi_stats.residual_norm,
            phi_solver_method=phi_stats.method,
        )

    def _assemble_rhs(self, state: SimulationState, phi: np.ndarray) -> np.ndarray:
        """Assemble the explicit IMEX right-hand side for psi.

        Inactive cells are forced to zero here so masked-domain invariants do not depend on the
        downstream linear solve or active-cell scatter path.
        """

        dt = self.config.time.dt
        rhs = (self.config.physics.u / dt) * state.psi
        rhs += (self.alpha - np.abs(state.psi) ** 2) * state.psi
        rhs += -1j * self.config.physics.u * phi * state.psi
        rhs[~self.mask.cell_active] = 0.0
        return rhs

    def _solve_psi(self, rhs: np.ndarray, links: LinkVariables) -> LinearSolveResult:
        """Solve the active-cell IMEX linear system for psi."""

        operator_active = build_active_psi_operator(
            self.grid,
            self.mask,
            links,
            self.active_cells,
            u=self.config.physics.u,
            dt=self.config.time.dt,
        )
        rhs_active = self.active_cells.flatten_active(rhs)
        return self.backend.solve(
            operator_active,
            rhs_active,
            method=self.config.solver.psi_linear_solver,
            rtol=self.config.solver.rtol,
            atol=self.config.solver.atol,
            max_it=self.config.solver.max_it,
        )

    def _sample_additive_noise(self, state: SimulationState) -> np.ndarray:
        """Sample one additive complex Gaussian field from the run-local RNG."""

        if not self.config.noise.enabled:
            return np.zeros_like(state.psi)
        if state.rng_state is None:
            raise SolverDivergenceError("stochastic noise requested without a run-local RNG")

        real = state.rng_state.standard_normal(size=state.psi.shape)
        imag = state.rng_state.standard_normal(size=state.psi.shape)
        noise = self.config.noise.strength * (real + 1j * imag) / np.sqrt(2.0)
        noise[~self.mask.cell_active] = 0.0
        return noise

    @staticmethod
    def _validate_field(name: str, field: np.ndarray) -> None:
        """Raise a structured solver error when a field becomes non-finite."""

        if not np.isfinite(field).all():
            raise SolverDivergenceError(f"NaN or inf detected in {name}")

    def align_state(self, state: SimulationState) -> SimulationState:
        """Refresh phi, A, and A_dot so they match the state's psi and timestamp."""

        context = self._build_step_context(state.psi, state.t)
        self._validate_field("phi", context.phi)
        diagnostics = dict(state.diagnostics)
        diagnostics.update(
            {
                "phi_iterations": context.phi_iterations,
                "phi_residual_norm": context.phi_residual_norm,
                "phi_solver_method": context.phi_solver_method,
            }
        )
        return SimulationState(
            grid=self.grid,
            t=state.t,
            step=state.step,
            psi=state.psi,
            phi=context.phi,
            A=context.A,
            A_dot=context.A_dot,
            diagnostics=diagnostics,
            rng_state=state.rng_state,
            checkpoint_id=state.checkpoint_id,
        )

    def advance(self, state: SimulationState) -> SimulationState:
        """Advance the TDGL state by one IMEX step."""

        next_t = state.t + self.config.time.dt
        # The first phi solve uses the old psi and new forcing to form the explicit coupling
        # terms. The second solve re-aligns diagnostics and normal-current inputs with psi_{n+1}.
        solve_context = self._build_step_context(state.psi, next_t)
        rhs = self._assemble_rhs(state, solve_context.phi)
        result = self._solve_psi(rhs, solve_context.links)
        psi_next = self.active_cells.scatter_active(result.solution, dtype=np.complex128)
        psi_next = psi_next + self._sample_additive_noise(state)
        psi_next[~self.mask.cell_active] = 0.0
        self._validate_field("psi", psi_next)
        final_context = self._build_step_context(psi_next, next_t)
        self._validate_field("phi", final_context.phi)

        diagnostics = {
            "step": state.step + 1,
            "psi_iterations": result.iterations,
            "psi_residual_norm": result.residual_norm,
            "psi_solver_method": result.method,
            "phi_iterations": solve_context.phi_iterations + final_context.phi_iterations,
            "phi_residual_norm": final_context.phi_residual_norm,
            "phi_solver_method": final_context.phi_solver_method,
        }
        return SimulationState(
            grid=self.grid,
            t=next_t,
            step=state.step + 1,
            psi=psi_next,
            phi=final_context.phi,
            A=final_context.A,
            A_dot=final_context.A_dot,
            diagnostics=diagnostics,
            rng_state=state.rng_state,
            checkpoint_id=state.checkpoint_id,
        )

    def compute_currents(self, state: SimulationState):
        """Compute currents consistent with the state's psi, phi, and forcing."""

        links = build_link_variables(self.grid, state.A)
        supercurrent = compute_supercurrent(self.grid, self.mask, state.psi, links)
        normal_current = compute_normal_current(self.grid, self.mask, state.phi, state.A_dot, self.config.physics.sigma_n)
        return links, supercurrent, normal_current

