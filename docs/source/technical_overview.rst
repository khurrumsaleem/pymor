.. _technical_overview:

******************
Technical Overview
******************

Three Central Classes
---------------------

From a bird's eye perspective, pyMOR is a collection of generic algorithms
operating on objects of the following types:

|VectorArrays|
    Vector arrays are ordered collections of vectors. Each vector of the array
    must be of the same |dimension|. Vectors can be |copied| to a new array,
    |appended| to an existing array or |removed| from the array. Basic linear
    algebra operations can be performed on the vectors of the
    array: vectors can be |scaled| in-place, the BLAS |axpy| operation is
    supported and |inner products| between vectors can be formed. Linear
    combinations of vectors can be formed using the |lincomb| method. Moreover,
    various norms can be computed and selected |dofs| of the vectors can
    be extracted for :mod:`empirical interpolation <pymor.algorithms.ei>`.
    To act on subsets of vectors of an array, arrays can be |indexed| with an
    integer, a list of integers or a slice, in each case returning a new
    |VectorArray| which acts as a modifiable view onto the respective vectors in
    the original array. As a convenience, many of Python's math operators are
    implemented in terms of the interface methods.

    Note that there is not the notion of a single vector in pyMOR. The main
    reason for this design choice is to take advantage of vectorized
    implementations like |NumpyVectorArray| which internally store the vectors
    as two-dimensional |NumPy| arrays. As an example, the application of a
    linear matrix based operator to an array via the |apply| method boils down
    to a call to |NumPy|'s optimized :meth:`~numpy.ndarray.dot` method. If
    there were only lists of vectors in pyMOR, the above matrix-matrix
    multiplication would have to be expressed by a loop of matrix-vector
    multiplications.  However, when working with external solvers, vector
    arrays will often be given as lists of individual vector objects. For this
    use-case we provide |ListVectorArray|, a |VectorArray| based on a Python
    list of vectors.

    Associated to each vector array is a |VectorSpace| which acts as a
    factory for new arrays of a given type.  New vector arrays can be created
    using the |zeros| and |empty| methods. To wrap the raw objects of the
    underlying linear algebra backend into a new |VectorArray|, |make_array|
    is used.

    The data needed to define a new |VectorSpace| largely depends on the
    implementation of the underlying backend. For |NumpyVectorSpace|, the
    only required datum is the dimension of the contained vectors.
    |VectorSpaces| for other backends could, e.g., hold a socket for
    communication with a specific PDE solver instance.

    Two arrays in pyMOR are compatible (e.g. can be added) if they are from
    the same |VectorSpace|. If a |VectorArray| is contained in a given
    |VectorSpace| can be tested with the `in` operator.

    .. |apply|            replace:: :meth:`~pymor.operators.interface.Operator.apply`
    .. |appended|         replace:: :meth:`appended <pymor.vectorarrays.interface.VectorArray.append>`
    .. |axpy|             replace:: :meth:`~pymor.vectorarrays.interface.VectorArray.axpy`
    .. |dofs|             replace:: :meth:`~pymor.vectorarrays.interface.VectorArray.dofs`
    .. |copied|           replace:: :meth:`copied <pymor.vectorarrays.interface.VectorArray.copy>`
    .. |dimension|        replace:: :attr:`dimension <pymor.vectorarrays.interface.VectorArray.dim>`
    .. |empty|            replace:: :meth:`~pymor.vectorarrays.interface.VectorSpace.empty`
    .. |indexed|          replace:: :meth:`!indexed`
    .. |inner products|   replace:: :meth:`inner products <pymor.vectorarrays.interface.VectorArray.inner>`
    .. |lincomb|          replace:: :meth:`~pymor.vectorarrays.interface.VectorArray.lincomb`
    .. |make_array|       replace:: :meth:`~pymor.vectorarrays.interface.VectorSpace.make_array`
    .. |removed|          replace:: :meth:`!deleted`
    .. |scaled|           replace:: :meth:`scaled <pymor.vectorarrays.interface.VectorArray.scal>`
    .. |zeros|            replace:: :meth:`~pymor.vectorarrays.interface.VectorSpace.zeros`

|Operators|
    The main property of operators in pyMOR is that they can be |applied| to
    |VectorArrays| resulting in a new |VectorArray|. For this operation to be
    allowed, the operator's |source| |VectorSpace| must be identical with the
    |VectorSpace| of the given array. The result will be a vector array from
    the |range| space. An operator can be |linear| or not.  The |apply_inverse|
    method provides an interface for (linear) solvers.

    Operators in pyMOR are also used to represent bilinear forms via the
    |apply2| method. A functional in pyMOR is simply an operator with
    `NumpyVectorSpace(1)` as |range|. Dually, a vector-like operator is an operator
    with `NumpyVectorSpace(1)` as |source|. Such vector-like operators are used
    in pyMOR to represent |Parameter|-dependent vectors such as the initial data
    of an |InstationaryModel|. For linear functionals and vector-like
    operators, the |as_vector| method can be called to obtain a vector
    representation of the operator as a |VectorArray| of length 1.

    Linear combinations of operators can be formed using a |LincombOperator|.
    When such a linear combination is |assembled|, |_assemble_lincomb|
    is called to ensure that, for instance, linear combinations of operators
    represented by a matrix lead to a new operator holding the linear
    combination of the matrices.

    For many interface methods default implementations are provided which
    may be overridden with operator-specific code. Base classes for |NumPy|-based
    operators can be found in :mod:`pymor.operators.numpy`. Several methods for
    constructing new operators from existing ones are contained in
    :mod:`pymor.operators.constructions`.

    .. |applied|           replace:: :meth:`applied <pymor.operators.interface.Operator.apply>`
    .. |apply2|            replace:: :meth:`~pymor.operators.interface.Operator.apply2`
    .. |apply_inverse|     replace:: :meth:`~pymor.operators.interface.Operator.apply_inverse`
    .. |assembled|         replace:: :meth:`assembled <pymor.operators.interface.Operator.assemble>`
    .. |_assemble_lincomb| replace:: :meth:`~pymor.operators.interface.Operator._assemble_lincomb`
    .. |as_vector|         replace:: :meth:`~pymor.operators.interface.Operator.as_vector`
    .. |linear|            replace:: :attr:`~pymor.operators.interface.Operator.linear`
    .. |range|             replace:: :attr:`~pymor.operators.interface.Operator.range`
    .. |source|            replace:: :attr:`~pymor.operators.interface.Operator.source`

|Models|
    Models in pyMOR encode the mathematical structure of a given
    discrete problem by acting as container classes for |Operators|. Each
    model object has |Operators| and the |products| dictionary of |Operators|
    which appear in the formulation of the discrete problem. The keys in the
    |products| dictionary describe the role of the respective product in the
    discrete problem.

    Apart from describing the discrete problem, models also implement
    algorithms for |solving| the given problem, returning |VectorArrays|
    from the |solution_space|. The solution can be |cached|, s.t.
    subsequent solving of the problem for the same |parameter values| reduces
    to looking up the solution in pyMOR's cache. To get an overview, which
    methods can be cached in pyMOR, use :func:`~pymor.core.cache.print_cached_methods`.

    While special model classes may be implemented which make use of
    the specific types of operators they contain (e.g. using some external
    high-dimensional solver for the problem), it is generally favorable to
    implement the solution algorithms only through the interfaces provided by
    the operators contained in the model, as this allows to use the
    same model class to solve high-dimensional and reduced problems.
    This has been done for the simple stationary and instationary
    models found in :mod:`pymor.models.basic`.

    Models can also implement |estimate| and |visualize| methods to
    estimate the discretization or model reduction error of a computed solution
    and create graphic representations of |VectorArrays| from the
    |solution_space|.

    .. |cached|           replace:: :mod:`cached <pymor.core.cache>`
    .. |estimate|         replace:: :meth:`~pymor.models.interface.Model.estimate_error`
    .. |products|         replace:: :attr:`~pymor.models.interface.Model.products`
    .. |solution_space|   replace:: :attr:`~pymor.models.interface.Model.solution_space`
    .. |solve|            replace:: :meth:`~pymor.models.interface.Model.solve`
    .. |solving|          replace:: :meth:`solving <pymor.models.interface.Model.solve>`
    .. |visualize|        replace:: :meth:`~pymor.models.interface.Model.visualize`


Base Classes
------------

While |VectorArrays| are mutable objects, both |Operators| and |Models|
are immutable in pyMOR: the application of an |Operator| to the same
|VectorArray| will always lead to the same result, solving a |Model|
for the same parameter will always produce the same solution array. This has two
main benefits:

1. If multiple objects/algorithms hold references to the same
   |Operator| or |Model|, none of the objects has to worry that the
   referenced object changes without their knowledge.
2. The return value of a method of an immutable object only depends on its
   arguments, allowing reliable |caching| of these return values.

A class can be made immutable in pyMOR by deriving from |ImmutableObject|,
which ensures that write access to the object's attributes is prohibited after
`__init__` has been executed. However, note that changes to private attributes
(attributes whose name starts with `_`) are still allowed. It lies in the
implementors responsibility to ensure that changes to these attributes do not
affect the outcome of calls to relevant interface methods. As an example, a call
to :meth:`~pymor.core.cache.CacheableObject.enable_caching` will set the
objects private `__cache_region` attribute, which might affect the speed of a
subsequent |solve| call, but not its result.

Of course, in many situations one may wish to change properties of an immutable
object, e.g. the number of timesteps for a given model. This can be
easily achieved using the
:meth:`~pymor.core.base.ImmutableObject.with_` method every immutable
object has: a call of the form ``o.with_(a=x, b=y)`` will return a copy of `o`
in which the attribute `a` now has the value `x` and the attribute `b` the
value `y`. It can be generally assumed that calls to
:meth:`~pymor.core.base.ImmutableObject.with_` are inexpensive. The
set of allowed arguments can be found in the
:attr:`!_init_arguments` attribute.

All immutable classes in pyMOR and most other classes derive from
|BasicObject| which, through its meta class, provides several convenience
features for pyMOR. Most notably, every subclass of |BasicObject| obtains its
own :attr:`~pymor.core.base.BasicObject.logger` instance with a class
specific prefix.

.. |caching|        replace:: :mod:`caching <pymor.core.cache>`


Creating Models
---------------

pyMOR ships a small (and still quite incomplete) framework for creating finite
element or finite volume discretizations based on the `NumPy/Scipy
<https://scipy.org>`_ software stack. To end up with an appropriate
|Model|, one starts by instantiating an |analytical problem| which
describes the problem we want to discretize. |analytical problems| contain
|Functions| which define the analytical data functions associated with the
problem and a |DomainDescription| that provides a geometrical definition of the
domain the problem is posed on and associates a boundary type to each part of
its boundary.

To obtain a |Model| from an |analytical problem| we use a
:mod:`discretizer <pymor.discretizers>`. A discretizer will first mesh the
computational domain by feeding the |DomainDescription| into a
:mod:`domaindiscretizer <pymor.discretizers.builtin.domaindiscretizers>`
which will return the |Grid| along with a |BoundaryInfo| associating boundary
entities with boundary types. Next, the |Grid|, |BoundaryInfo| and the various
data functions of the |analytical problem| are used to instatiate
:mod:`finite element <pymor.discretizers.builtin.cg>` or
:mod:`finite volume <pymor.discretizers.builtin.fv>` operators.
Finally these operators are used to instatiate one of the provided
|Model| classes.

In pyMOR, |analytical problems|, |Functions|, |DomainDescriptions|,
|BoundaryInfos| and |Grids| are all immutable, enabling efficient
disk |caching| for the resulting |Models|, persistent over various
runs of the applications written with pyMOR.

While pyMOR's internal discretizations are useful for getting started quickly
with model reduction experiments, pyMOR's main goal is to allow the reduction of
models provided by external solvers. In order to do so, all that needs
to be done is to provide |VectorArrays|, |Operators| and |Models| which
interact appropriately with the solver. pyMOR makes no assumption on how the
communication with the solver is managed. For instance, communication could take
place via a network protocol or job files.  In particular it should be stressed
that in general no communication of high-dimensional data between the solver
and pyMOR is necessary: |VectorArrays| can merely hold handles to data in the
solver's memory or some on-disk database. Where possible, we favor, however, a
deep integration of the solver with pyMOR by linking the solver code as a Python
extension module. This allows Python to directly access the solver's data
structures which can be used to quickly add features to the high-dimensional
code without any recompilation. A minimal example for such an integration using
`pybind11 <https://github.com/pybind/pybind11>`_ can be found in the
``src/pymordemos/minimal_cpp_demo`` directory of the pyMOR repository.
Bindings for `FEnicS <https://fenicsproject.org>`_ and
`NGSolve <https://ngsolve.org>`_ packages are available in the
:mod:`bindings.fenics <pymor.bindings.fenics>` and
:mod:`bindings.ngsolve <pymor.bindings.ngsolve>` modules.
The `pymor-deal.II <https://github.com/pymor/pymor-deal.II>`_ repository contains
bindings for `deal.II <https://dealii.org>`_.


Parameters
----------

pyMOR classes implement dependence on a parameter by deriving from the
|ParametricObject| base class. This class gives each instance a
:attr:`~pymor.parameters.base.ParametricObject.parameters` attribute describing the
|Parameters| the object and its relevant methods (`apply`, `solve`, `evaluate`, etc.)
depend on. Each |Parameter| in pyMOR has a name and a fixed dimension, i.e. the
number of scalar components of the |Parameter|. Scalar parameters are simply
represented by one-dimensional |Parameters|. To assign concrete values to |Parameters|
the specialized dict-like class :class:`~pymor.parameters.base.Mu` is used.
In particular, it ensures, that all of its values are one-dimensional |NumPy arrays|.

The |Parameters| of a |ParametricObject| are usually automatically derived
as the union of all |Parameters| of the objects that are passed to it's `__init__` method.
For instance, an |Operator| that implements the L2-product with some user-provided
|Function| will automatically inherit all |Parameters| of that |Function|.
Additional |Parameters| can be easily added by setting the
:attr:`!parameters_own` attribute.


Defaults
--------

pyMOR offers a convenient mechanism for handling default values such as solver
tolerances, cache sizes, log levels, etc. Each default in pyMOR is the default
value of an optional argument of some function. Such an argument is made a
default by decorating the function with the :func:`~pymor.core.defaults.defaults`
decorator::

    @defaults('tolerance')
    def some_algorithm(x, y, tolerance=1e-5)
        ...

Default values can be changed by calling :func:`~pymor.core.defaults.set_defaults`.
By calling :func:`~pymor.core.defaults.print_defaults` a summary of all defaults
in pyMOR and their values can be printed. A configuration file with all defaults
can be obtained with :func:`~pymor.core.defaults.write_defaults_to_file`. This file can
then be loaded, either programmatically or automatically by setting the
``PYMOR_DEFAULTS`` environment variable.

As an additional feature, if ``None`` is passed as value for a function argument
which is a default, its default value is used instead of ``None``. This allows
writing code of the following form::

    def method_called_by_user(U, V, tolerance_for_algorithm=None):
        ...
        algorithm(U, V, tolerance=tolerance_for_algorithm)
        ...

See the :mod:`~pymor.core.defaults` module for more information.


RuleTables
----------

Many algorithms in pyMOR can be seen as transformations acting on trees of
|Operators|. One example is the structure-preserving (Petrov-)Galerkin
projection of |Operators| performed by the |project| method. For instance, a
|LincombOperator| is projected by replacing all its children (the |Operators|
forming the affine decomposition) with projected |Operators|.

During development of pyMOR, it turned out that using inheritance for selecting
the action to be taken to project a specific operator (i.e. single dispatch
based on the class of the to-be-projected |Operator|) is not sufficiently
flexible. With pyMOR 0.5 we have introduced algorithms which are based on
|RuleTables| instead of inheritance. A |RuleTable| is simply an ordered list of
:class:`rules <pymor.algorithms.rules.rule>`, i.e. pairs of conditions to match
with corresponding actions. When a |RuleTable| is :meth:`applied
<pymor.algorithms.rules.RuleTable.apply>` to an object (e.g. an |Operator|),
the action associated with the first matching rule in the table is executed. As
part of the action, the |RuleTable| can be easily :meth:`applied recursively
<pymor.algorithms.rules.RuleTable.apply_children>` to the children of the given
object.

This approach has several advantages over an inheritance-based model:

- Rules can match based on the class of the object, but also on more general
  conditions, i.e. the name of the |Operator| or being linear and non-|parametric|.

- The entire mathematical algorithm can be specified in a single file even when the
  definition of the possible classes the algorithm can be applied to is scattered
  over various files.

- The precedence of rules is directly apparent from the definition of the |RuleTable|.

- Generic rules (e.g. the projection of a linear non-|parametric| |Operator| by simply
  applying the basis) can be easily scheduled to take precedence over more specific
  rules.

- Users can implement or modify |RuleTables| without modification of the classes
  shipped with pyMOR.



The Reduction Process
---------------------

The reduction process in pyMOR is handled by so called :mod:`~pymor.reductors`,
where each reductor takes arbitrary |Models| of associated type, and additional
data (e.g. the reduced basis) to create reduced |Models|. For instance, the
:class:`~pymor.reductors.basic.StationaryRBReductor` and
:class:`~pymor.reductors.basic.InstationaryRBReductor` reductors can reduce any
:class:`~pymor.models.basic.StationaryModel` and :class:`~pymor.models.basic.InstationaryModel`,
while the :class:`~pymor.reductors.bt.BTReductor` reduces
:class:`~pymor.models.iosys.LTIModel` (just to name a few).

If proper offline/online decomposition is achieved by the reductor, the reduced
|Model| will not store any high-dimensional data. Note that there is no inherent
distinction between low- and high-dimensional |Models| in pyMOR. The only
difference lies in the different types of operators, the |Model|
contains.

In particular, in most projection-based MOR methods, only the
|Operators| of a given |Model| are projected onto the
reduced-basis space, whereas the structure of the problem
(i.e. the type of the |Model|) stays the same.
The actual projection of an individual |Operator| is performed by the generic
:meth:`~pymor.algorithms.projection.project` algorithm, which is able to perform a
Petrov-Galerkin projection of any |Operator| available to pyMOR.
The algorithm automatically exploits the structure of the given |Operator|
(linearity, parameter separability, etc.) where possible
to decouple the evaluation of the projected |Operator| from any high-dimensional spaces.

In addition to the projection of the |Model|, reductors may also assemble efficient
offline-online decomposed a posterior error estimates (available via the
`estimate_error` method of the resulting reduced order |Model|), if more information
about the underlying problem yielding the full order |Model| is available
(a popular example is the :class:`~pymor.reductors.coercive.CoerciveRBReductor` for |Models| representing stationary
coercive problems).

If you want to further dive into the inner workings of pyMOR, we
recommend to study the :doc:`Projecting a Model <tutorial_projection>` tutorial.
