#!/usr/bin/env python3
# This file is part of the pyMOR project (https://www.pymor.org).
# Copyright pyMOR developers and contributors. All rights reserved.
# License: BSD 2-Clause License (https://opensource.org/licenses/BSD-2-Clause)

import time

import numpy as np
from typer import Argument, Option, run

from pymor.basic import *
from pymor.core.config import config
from pymor.reductors.neural_network import (
    NeuralNetworkLSTMReductor,
    NeuralNetworkLSTMStatefreeOutputReductor,
    NeuralNetworkReductor,
    NeuralNetworkStatefreeOutputReductor,
)
from pymor.tools import mpi


def main(
    problem_number: int = Argument(..., min=0, max=1, help='Selects the problem to solve [0 or 1].'),
    grid_intervals: int = Argument(..., help='Grid interval count.'),
    time_steps: int = Argument(..., help='Number of time steps used for discretization.'),
    training_samples: int = Argument(..., help='Number of samples used for training the neural network.'),
    validation_samples: int = Argument(..., help='Number of samples used for validation during the training phase.'),
    plot_test_solutions: bool = Option(False, help='Plot FOM and ROM solutions of the test parameters.'),
):
    """Model order reduction with neural networks for instationary problems.

    Problem number 0 considers the incompressible Navier-Stokes equations in
    a two-dimensional cavity with the Reynolds number as parameter.
    The discretization is based on FEniCS.

    Problem number 1 considers a parametrized Burgers equation on a
    one-dimensional domain. The discretization is based on pyMOR's built-in
    functionality.
    """
    config.require('TORCH')

    fom, plot_function = create_fom(problem_number, grid_intervals, time_steps)

    if problem_number == 0:
        parameter_space = fom.parameters.space(1., 50.)
    else:
        parameter_space = fom.parameters.space(1., 2.)

    training_parameters = parameter_space.sample_uniformly(training_samples)
    validation_parameters = parameter_space.sample_randomly(validation_samples)
    test_parameters = parameter_space.sample_randomly(10)

    def compute_errors_state(rom, reductor):
        speedups = []

        print(f'Performing test on parameters of size {len(test_parameters)} ...')

        U = fom.solution_space.empty(reserve=len(test_parameters))
        U_red = fom.solution_space.empty(reserve=len(test_parameters))

        for mu in test_parameters:
            tic = time.time()
            u_fom = fom.solve(mu)[1:]
            U.append(u_fom)
            time_fom = time.time() - tic
            if plot_test_solutions and plot_function:
                plot_function(u_fom, title='FOM')

            tic = time.time()
            u_red = reductor.reconstruct(rom.solve(mu))[1:]
            U_red.append(u_red)
            time_red = time.time() - tic
            if plot_test_solutions and plot_function:
                plot_function(u_red, title='ROM')

            speedups.append(time_fom / time_red)

        absolute_errors = (U - U_red).norm2()
        relative_errors = (U - U_red).norm2() / U.norm2()

        return absolute_errors, relative_errors, speedups

    reductor = NeuralNetworkReductor(fom=fom, training_parameters=training_parameters,
                                     validation_parameters=validation_parameters, basis_size=10,
                                     scale_outputs=True, ann_mse=None)
    rom = reductor.reduce(hidden_layers='[30, 30, 30]', restarts=0)

    abs_errors, rel_errors, speedups = compute_errors_state(rom, reductor)

    reductor_lstm = NeuralNetworkLSTMReductor(fom=fom, training_parameters=training_parameters,
                                              validation_parameters=validation_parameters, basis_size=10,
                                              scale_inputs=False, scale_outputs=True, ann_mse=None)
    rom_lstm = reductor_lstm.reduce(restarts=0, number_layers=3, learning_rate=0.1)

    abs_errors_lstm, rel_errors_lstm, speedups_lstm = compute_errors_state(rom_lstm, reductor_lstm)

    def compute_errors_output(output_rom):
        outputs = []
        outputs_red = []
        outputs_speedups = []

        print(f'Performing test on parameters of size {len(test_parameters)} ...')

        for mu in test_parameters:
            tic = time.perf_counter()
            outputs.append(fom.compute(output=True, mu=mu)['output'][1:])
            time_fom = time.perf_counter() - tic
            tic = time.perf_counter()
            outputs_red.append(output_rom.compute(output=True, mu=mu)['output'][1:])
            time_red = time.perf_counter() - tic

            outputs_speedups.append(time_fom / time_red)

        outputs = np.squeeze(np.array(outputs))
        outputs_red = np.squeeze(np.array(outputs_red))

        outputs_absolute_errors = np.abs(outputs - outputs_red)
        outputs_relative_errors = np.abs(outputs - outputs_red) / np.abs(outputs)

        return outputs_absolute_errors, outputs_relative_errors, outputs_speedups

    output_reductor = NeuralNetworkStatefreeOutputReductor(fom=fom, nt=time_steps+1,
                                                           training_parameters=training_parameters,
                                                           validation_parameters=validation_parameters,
                                                           validation_loss=1e-5, scale_outputs=True)
    output_rom = output_reductor.reduce(restarts=100)

    outputs_abs_errors, outputs_rel_errors, outputs_speedups = compute_errors_output(output_rom)

    output_reductor_lstm = NeuralNetworkLSTMStatefreeOutputReductor(fom=fom, nt=time_steps + 1,
                                                                    training_parameters=training_parameters,
                                                                    validation_parameters=validation_parameters,
                                                                    validation_loss=None, scale_inputs=False,
                                                                    scale_outputs=True)
    output_rom_lstm = output_reductor_lstm.reduce(restarts=0, number_layers=3, hidden_dimension=50,
                                                  learning_rate=0.1)

    outputs_abs_errors_lstm, outputs_rel_errors_lstm, outputs_speedups_lstm = compute_errors_output(output_rom_lstm)

    print()
    print('Approach by Hesthaven and Ubbiali using feedforward ANNs:')
    print('=========================================================')
    print('Results for state approximation:')
    print(f'Average absolute error: {np.average(abs_errors)}')
    print(f'Average relative error: {np.average(rel_errors)}')
    print(f'Median of speedup: {np.median(speedups)}')

    print()
    print('Results for output approximation:')
    print(f'Average absolute error: {np.average(outputs_abs_errors)}')
    print(f'Average relative error: {np.average(outputs_rel_errors)}')
    print(f'Median of speedup: {np.median(outputs_speedups)}')

    print()
    print()
    print('Approach using long short-term memory ANNs:')
    print('===========================================')

    print('Results for state approximation:')
    print(f'Average absolute error: {np.average(abs_errors_lstm)}')
    print(f'Average relative error: {np.average(rel_errors_lstm)}')
    print(f'Median of speedup: {np.median(speedups_lstm)}')

    print()
    print('Results for output approximation:')
    print(f'Average absolute error: {np.average(outputs_abs_errors_lstm)}')
    print(f'Average relative error: {np.average(outputs_rel_errors_lstm)}')
    print(f'Median of speedup: {np.median(outputs_speedups_lstm)}')


def create_fom(problem_number, grid_intervals, time_steps):
    print('Discretize ...')
    if problem_number == 0:
        config.require('FENICS')
        fom, plot_function = discretize_navier_stokes(grid_intervals, time_steps)
    elif problem_number == 1:
        problem = burgers_problem()
        f = LincombFunction(
            [ExpressionFunction('1.', 1), ConstantFunction(1., 1)],
            [ProjectionParameterFunctional('exponent'), 0.1])
        problem = problem.with_stationary_part(outputs=[('l2', f)])

        fom, _ = discretize_instationary_fv(problem, diameter=1. / grid_intervals, nt=time_steps)
        plot_function = fom.visualize
    else:
        raise ValueError(f'Unknown problem number {problem_number}')

    return fom, plot_function


def discretize_navier_stokes(n, nt):
    if mpi.parallel:
        from pymor.models.mpi import mpi_wrap_model
        fom = mpi_wrap_model(lambda: _discretize_navier_stokes(n, nt),
                             use_with=True, pickle_local_spaces=False)
        plot_function = None
    else:
        fom, plot_function = _discretize_navier_stokes(n, nt)
    return fom, plot_function


def _discretize_navier_stokes(n, nt):
    import dolfin as df
    import matplotlib.pyplot as plt

    from pymor.algorithms.timestepping import ImplicitEulerTimeStepper
    from pymor.bindings.fenics import FenicsMatrixOperator, FenicsOperator, FenicsVectorSpace, FenicsVisualizer

    # create square mesh
    mesh = df.UnitSquareMesh(n, n)

    # create Finite Elements for the pressure and the velocity
    P = df.FiniteElement('P', mesh.ufl_cell(), 1)
    V = df.VectorElement('P', mesh.ufl_cell(), 2, dim=2)
    # create mixed element and function space
    TH = df.MixedElement([P, V])
    W = df.FunctionSpace(mesh, TH)

    # extract components of mixed space
    W_p = W.sub(0)
    W_u = W.sub(1)

    # define trial and test functions for mass matrix
    u = df.TrialFunction(W_u)
    psi_u = df.TestFunction(W_u)

    # assemble mass matrix for velocity
    mass_mat = df.assemble(df.inner(u, psi_u) * df.dx)

    # define trial and test functions
    psi_p, psi_u = df.TestFunctions(W)
    w = df.Function(W)
    p, u = df.split(w)

    # set Reynolds number, which will serve as parameter
    Re = df.Constant(1.)

    # define walls
    top_wall = 'near(x[1], 1.)'
    walls = 'near(x[0], 0.) | near(x[0], 1.) | near(x[1], 0.)'

    # define no slip boundary conditions on all but the top wall
    bcu_noslip_const = df.Constant((0., 0.))
    bcu_noslip  = df.DirichletBC(W_u, bcu_noslip_const, walls)
    # define Dirichlet boundary condition for the velocity on the top wall
    bcu_lid_const = df.Constant((1., 0.))
    bcu_lid = df.DirichletBC(W_u, bcu_lid_const, top_wall)

    # fix pressure at a single point of the domain to obtain unique solutions
    pressure_point = 'near(x[0],  0.) & (x[1] <= ' + str(2./n) + ')'
    bcp_const = df.Constant(0.)
    bcp = df.DirichletBC(W_p, bcp_const, pressure_point)

    # collect boundary conditions
    bc = [bcu_noslip, bcu_lid, bcp]

    mass = -psi_p * df.div(u)
    momentum = (df.dot(psi_u, df.dot(df.grad(u), u))
                - df.div(psi_u) * p
                + 2.*(1./Re) * df.inner(df.sym(df.grad(psi_u)), df.sym(df.grad(u))))
    F = (mass + momentum) * df.dx

    df.solve(F == 0, w, bc)

    # define pyMOR operators
    space = FenicsVectorSpace(W)
    mass_op = FenicsMatrixOperator(mass_mat, W, W, name='mass')
    op = FenicsOperator(F, space, space, w, bc,
                        parameter_setter=lambda mu: Re.assign(mu['Re'].item()),
                        parameters={'Re': 1})

    # timestep size for the implicit Euler timestepper
    dt = 0.01
    ie_stepper = ImplicitEulerTimeStepper(nt=nt)

    # define initial condition and right hand side as zero
    fom_init = VectorOperator(op.range.zeros())
    rhs = VectorOperator(op.range.zeros())
    # define output functional
    output_func = VectorFunctional(op.range.ones())

    # construct instationary model
    fom = InstationaryModel(dt * nt,
                            fom_init,
                            op,
                            rhs,
                            mass=mass_op,
                            time_stepper=ie_stepper,
                            output_functional=output_func,
                            visualizer=FenicsVisualizer(space))

    def plot_fenics(w, title=''):
        v = df.Function(W)
        v.leaf_node().vector()[:] = (w.to_numpy()[:, -1]).squeeze()
        p, u  = v.split()

        fig_u = df.plot(u)
        plt.title('Velocity vector field ' + title)
        plt.xlabel('$x$')
        plt.ylabel('$y$')
        plt.colorbar(fig_u)
        plt.show()

        fig_p = df.plot(p)
        plt.title('Pressure field ' + title)
        plt.xlabel('$x$')
        plt.ylabel('$y$')
        plt.colorbar(fig_p)
        plt.show()

    if mpi.parallel:
        return fom
    else:
        return fom, plot_fenics


if __name__ == '__main__':
    run(main)
