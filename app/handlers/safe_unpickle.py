"""Restricted unpickling for client-uploaded model files.

`on_load_model` / `on_add_model` in websocket.py accept pickled
`digital_twinning.PredictiveModel` objects uploaded by any connected client.
Plain `pickle.loads()` on attacker-controlled bytes is remote code execution
(a crafted pickle can invoke arbitrary callables via `__reduce__`).

This module is defense-in-depth, NOT a perfect sandbox. It allows unpickling
of classes/functions from a broad set of trusted module namespaces (the
legitimate dependency surface of a trained PredictiveModel: numpy, pandas,
sklearn, torch, xgboost/catboost/lightgbm, digital_twinning, and friends),
while hard-blocking a small list of universally dangerous callables
(os/subprocess/eval/exec/etc.) regardless of which module they'd otherwise
be allowed under. This stops the standard generic RCE gadgets used against
pickle, but a sufficiently obscure `__reduce__` gadget living inside an
allowed library is theoretically still possible - restricting the module
namespace narrows the attack surface, it does not eliminate it. If a
stronger guarantee is needed later, run the unpickling step in a separate
sandboxed/resource-limited process instead of (or in addition to) this.
"""

import io
import pickle

# Entire modules that legitimate PredictiveModel graphs may reference.
# Broad on purpose - hand-picking individual classes here breaks the moment
# the ML libraries add/rename an internal class used during unpickling.
ALLOWED_MODULE_PREFIXES = (
    "numpy",
    "pandas",
    "sklearn",
    "scipy",
    "torch",
    "xgboost",
    "catboost",
    "lightgbm",
    "digital_twinning",
    "gPCE_model",
    "uncertain_variables",
    "shap",
    "SALib",
    "collections",
)

# Exact (module, name) targets that are always blocked, even if their module
# prefix is otherwise allowed - these are generic RCE primitives, not
# anything a trained model legitimately needs to reference.
BLOCKED_CALLABLES = {
    ("os", "system"), ("os", "popen"), ("os", "execv"), ("os", "execve"),
    ("os", "spawnv"), ("os", "spawnve"), ("os", "fork"),
    ("nt", "system"), ("posix", "system"),
    ("subprocess", "Popen"), ("subprocess", "call"), ("subprocess", "run"),
    ("subprocess", "check_output"), ("subprocess", "check_call"),
    ("shutil", "rmtree"), ("shutil", "move"),
    ("socket", "socket"),
    ("pty", "spawn"),
    ("builtins", "eval"), ("builtins", "exec"), ("builtins", "compile"),
    ("builtins", "__import__"), ("builtins", "open"), ("builtins", "input"),
}

SAFE_BUILTINS = {
    "dict", "list", "tuple", "set", "frozenset", "str", "bytes", "bytearray",
    "int", "float", "bool", "complex", "slice", "range", "object", "type",
    "getattr", "setattr", "type",
}


class RestrictedUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if (module, name) in BLOCKED_CALLABLES:
            raise pickle.UnpicklingError(f"Blocked unpickle target: {module}.{name}")
        if module == "builtins":
            if name not in SAFE_BUILTINS:
                raise pickle.UnpicklingError(f"Blocked unpickle target: {module}.{name}")
            return super().find_class(module, name)
        if any(module == p or module.startswith(p + ".") for p in ALLOWED_MODULE_PREFIXES):
            return super().find_class(module, name)
        raise pickle.UnpicklingError(f"Blocked unpickle target: {module}.{name}")


def restricted_loads(data: bytes):
    return RestrictedUnpickler(io.BytesIO(data)).load()
