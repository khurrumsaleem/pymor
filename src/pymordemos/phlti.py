#!/usr/bin/env python
# This file is part of the pyMOR project (https://www.pymor.org).
# Copyright pyMOR developers and contributors. All rights reserved.
# License: BSD 2-Clause License (https://opensource.org/licenses/BSD-2-Clause)

import numpy as np
from matplotlib import pyplot as plt
from typer import run, Option

from pymor.models.iosys import PHLTIModel
from pymor.reductors.bt import PRBTReductor
from pymor.reductors.ph.ph_irka import PHIRKAReductor


def msd(n=6, m=2, m_i=4, k_i=4, c_i=1, as_lti=False):
    """Mass-spring-damper model as (port-Hamiltonian) linear time-invariant system.

    Taken from :cite:`GPBV12`.

    Parameters
    ----------
    n
        The order of the model.
    m_i
        The weight of the masses.
    k_i
        The stiffness of the springs.
    c_i
        The amount of damping.
    as_lti
        If `True`, the matrices of the standard linear time-invariant system are returned,
        otherwise the matrices of the port-hamiltonian linear time-invariant system are returned.

    Returns
    -------
    A
        The lti |NumPy array| A, if `as_lti` is `True`.
    B
        The lti |NumPy array| B, if `as_lti` is `True`.
    C
        The lti |NumPy array| C, if `as_lti` is `True`.
    D
        The lti |NumPy array| D, if `as_lti` is `True`.
    J
        The ph |NumPy array| J, if `as_lti` is `False`.
    R
        The ph |NumPy array| R, if `as_lti` is `False`.
    G
        The ph |NumPy array| G, if `as_lti` is `False`.
    P
        The ph |NumPy array| P, if `as_lti` is `False`.
    S
        The ph |NumPy array| S, if `as_lti` is `False`.
    N
        The ph |NumPy array| N, if `as_lti` is `False`.
    E
        The lti |NumPy array| E, if `as_lti` is `True`, or
        the ph |NumPy array| E, if `as_lti` is `False`.
    """
    n = int(n / 2)

    A = np.array(
        [[0, 1 / m_i, 0, 0, 0, 0], [-k_i, -c_i / m_i, k_i, 0, 0, 0],
         [0, 0, 0, 1 / m_i, 0, 0], [k_i, 0, -2 * k_i, -c_i / m_i, k_i, 0],
         [0, 0, 0, 0, 0, 1 / m_i], [0, 0, k_i, 0, -2 * k_i, -c_i / m_i]])

    if m == 2:
        B = np.array([[0, 1, 0, 0, 0, 0], [0, 0, 0, 1, 0, 0]]).T
        C = np.array([[0, 1 / m_i, 0, 0, 0, 0], [0, 0, 0, 1 / m_i, 0, 0]])
    elif m == 1:
        B = np.array([[0, 1, 0, 0, 0, 0]]).T
        C = np.array([[0, 1 / m_i, 0, 0, 0, 0]])
    else:
        assert False

    J_i = np.array([[0, 1], [-1, 0]])
    J = np.kron(np.eye(3), J_i)
    R_i = np.array([[0, 0], [0, c_i]])
    R = np.kron(np.eye(3), R_i)

    for i in range(4, n + 1):
        B = np.vstack((B, np.zeros((2, m))))
        C = np.hstack((C, np.zeros((m, 2))))

        J = np.block([
            [J, np.zeros(((i - 1) * 2, 2))],
            [np.zeros((2, (i - 1) * 2)), J_i]
        ])

        R = np.block([
            [R, np.zeros(((i - 1) * 2, 2))],
            [np.zeros((2, (i - 1) * 2)), R_i]
        ])

        A = np.block([
            [A, np.zeros(((i - 1) * 2, 2))],
            [np.zeros((2, i * 2))]
        ])

        A[2 * i - 2, 2 * i - 2] = 0
        A[2 * i - 1, 2 * i - 1] = -c_i / m_i
        A[2 * i - 3, 2 * i - 2] = k_i
        A[2 * i - 2, 2 * i - 1] = 1 / m_i
        A[2 * i - 2, 2 * i - 3] = 0
        A[2 * i - 1, 2 * i - 2] = -2 * k_i
        A[2 * i - 1, 2 * i - 4] = k_i

    Q = np.linalg.solve(J - R, A)
    G = B
    P = np.zeros(G.shape)
    D = np.zeros((m, m))
    E = np.eye(2 * n)
    S = (D + D.T) / 2
    N = -(D - D.T) / 2

    if as_lti:
        return A, B, C, D, E

    return J, R, G, P, S, N, E, Q


def main(
        n: int = Option(100, help='Order of the Mass-Spring-Damper system.')
):
    J, R, G, P, S, N, E, Q = msd(n, m=2)
    fom = PHLTIModel.from_matrices(J, R, G, Q=Q)
    h2 = fom.h2_norm()

    prbt = PRBTReductor(fom)
    phirka = PHIRKAReductor(fom)

    reductors = {'pH-IRKA': phirka, 'PRBT': prbt}
    markers = {'pH-IRKA': 's', 'PRBT': 'o'}

    reduced_order = range(2, 22, 2)
    h2_errors = np.zeros((len(reductors), len(reduced_order)))

    for i, reductor in enumerate(reductors):
        for j, r in enumerate(reduced_order):
            rom = reductors[reductor].reduce(r)
            h2_errors[i, j] = (rom - fom).h2_norm() / h2

    plt.figure()
    for i, reductor in enumerate(reductors):
        plt.semilogy(reduced_order, h2_errors[i], label=reductor, marker=markers[reductor])

    plt.ylabel('Relative $\mathcal{H}_2$-error')
    plt.xlabel('Reduced order r')
    plt.legend()
    plt.show()

if __name__ == '__main__':
    run(main)
