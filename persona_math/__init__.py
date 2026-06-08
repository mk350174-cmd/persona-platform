"""
persona_math — The Unified Mathematical Library for Persona Engineering
M7: A Unified Mathematical Framework for Persona Engineering (55 Tools)

Modules:
    foundation      M01-M04  Vector, Shannon, Kolmogorov
    metrics         M05-M09  Spectroscopy, Drift, Fisher, IIT-Phi, Yoneda
    dynamics        M10-M15  ODE, Lyapunov, Arkhe, HJB
    topology        M16-M18  Betti, FractalDim, Manifold
    category        M19-M21  Sheaf, Functor, NaturalTransform
    consciousness   M22-M25  GWT, HOT, FreeEnergy, Hopfield
    probability     M26-M28  Markov, Bayes, MarkovBlanket
    network_game    M29-M32  ScaleFree, SmallWorld, Nash, LotkaVolterra
    tensor_spectral M33-M36  Tensor, Fiedler, Fourier, Adjoint
    scale_transform M37-M39  Renorm, ESS, Criticality
    quantum_analogy M40-M43  WaveCollapse, Bell, QuantumLogic, Morphological
    subjectivity    M44-M46  SelfAwareness, Heisenberg, Godel
    limits          M47-M49  Halting, Liar, Kant
    literature2025  M50-M55  Rigoli, ConsciousnessEq, URL, MUMBLE, Neuroperc, Manifold
    ceid                     CEID composite score
    d1_protocol              D1-D5 benchmark runner
"""

__version__ = "2.0.0"
__series__ = "M1-M60 Persona Engineering Research Series"

# params is the authoritative source for all numeric constants.
# Import it early so downstream modules can reference params.* safely.
from . import params  # noqa: F401
