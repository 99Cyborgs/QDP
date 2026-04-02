"""IMEX time stepping for deterministic TDGL evolution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from tdgl_rf.config.models import TDGLRFCaseConfig
from tdgl_rf.fields.currents import CurrentField
from tdgl_rf.exceptions import SolverDivergenceError
from tdgl_rf.fields.currents import compute_normal_current, compute_supercurrent
from tdgl_rf.fields.forcing import VectorPotential, evaluate_forcing
from tdgl_rf.fields.linkvars import LinkVariables, build_link_variables
from tdgl_rf.geometry.masks import GeometryMask, StructuredGrid2D
from tdgl_rf.solvers.linear_ops import ActiveCellMap, build_active_psi_operator
from tdgl_rf.solvers.phi_solver import ScalarPotentialSolver
from tdgl_rf.solvers.scipy_backend import LinearSolveResult, SciPyLinearBackend
from tdgl_rf.solvers.state import SimulationState


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
    """Deterministic phase-1 IMEX TDGL stepper."""

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

    def _build_step_context(self, state: SimulationState) -> TDGLStepContext:
        """Assemble forcing, links, supercurrent, and scalar potential for one step."""

        a, a_dot = evaluate_forcing(self.grid, self.config.forcing, state.t, config_dir=self.config_dir)
        links = build_link_variables(self.grid, a)
        supercurrent = compute_supercurrent(self.grid, self.mask, state.psi, links)
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
        """Assemble the explicit IMEX right-hand side for psi."""

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

    @staticmethod
    def _validate_field(name: str, field: np.ndarray) -> None:
        """Raise a structured solver error when a field becomes non-finite."""

        if not np.isfinite(field).all():
            raise SolverDivergenceError(f"NaN or inf detected in {name}")

    def advance(self, state: SimulationState) -> SimulationState:
        """Advance the deterministic TDGL state by one IMEX step."""

        context = self._build_step_context(state)
        rhs = self._assemble_rhs(state, context.phi)
        result = self._solve_psi(rhs, context.links)
        psi_next = self.active_cells.scatter_active(result.solution, dtype=np.complex128)
        self._validate_field("psi", psi_next)
        self._validate_field("phi", context.phi)

        diagnostics = {
            "step": state.step + 1,
            "psi_iterations": result.iterations,
            "psi_residual_norm": result.residual_norm,
            "psi_solver_method": result.method,
            "phi_iterations": context.phi_iterations,
            "phi_residual_norm": context.phi_residual_norm,
            "phi_solver_method": context.phi_solver_method,
        }
        return SimulationState(
            grid=self.grid,
            t=state.t + self.config.time.dt,
            step=state.step + 1,
            psi=psi_next,
            phi=context.phi,
            A=context.A,
            A_dot=context.A_dot,
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
