from typing import Any

from docstring_inheritance import _BaseDocstringInheritanceMeta
from docstring_inheritance.docstring_inheritors.numpy import (
    NumpyDocstringInheritor,
)


class NumpyModDocstringInheritor(NumpyDocstringInheritor):
    """Modified processor for NumPy docstring.

    Original processor has ``Parameters`` in `_ARGS_SECTION_NAMES` and
    ``Parameters`` of the class docstring is not inherited.
    By moving it to `_ARGS_SECTION_NAMES` directly, the class docstring is
    inherited.
    On the other hand, even if any of ``Parameters`` are removed in the
    inherited class, the inherited docstring is not removed both for class and
    method docstrings..
    """

    _ARGS_SECTION_ITEMS_NAMES = {
        "Other Parameters",
    }

    _SECTION_ITEMS_NAMES = _ARGS_SECTION_ITEMS_NAMES | {
        "Parameters",
        "Attributes",
        "Methods",
    }


inherit_numpy_mod_docstring = NumpyModDocstringInheritor()


class NumpyModDocstringInheritanceInitMeta(_BaseDocstringInheritanceMeta):
    """Modified Metaclass for inheriting docstrings in Numpy format.

    This is for with ``__init__`` in the class docstring.
    """

    def __init__(
        self,
        class_name: str,
        class_bases: tuple[type],
        class_dict: dict[str, Any],
    ) -> None:
        super().__init__(
            class_name,
            class_bases,
            class_dict,
            inherit_numpy_mod_docstring,
            init_in_class=True,
        )
