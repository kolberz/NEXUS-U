from __future__ import annotations

from importlib import metadata

from .base import Adapter, AdapterDescriptor
from .dafny import DafnyAdapter
from .discovery import DiscoveryAdapter
from .document import DocumentAdapter
from .lean import LeanAdapter
from .git_delivery import GitDeliveryAdapter
from .python_exec import PythonExecutionAdapter


_BUILTIN_DESCRIPTORS = {
    "document": AdapterDescriptor("document", "1", "builtin", ["document", "architecture", "policy"], ["execution"]),
    "python": AdapterDescriptor("python", "1", "builtin", ["software", "simulation", "experiment"], ["execution"], ["python"], False),
    "discovery": AdapterDescriptor("discovery", "1", "builtin", ["experiment", "model"], ["computation"]),
    "lean": AdapterDescriptor("lean", "1", "builtin", ["theorem"], ["kernel"], ["lean", "lake"]),
    "dafny": AdapterDescriptor("dafny", "1", "builtin", ["software", "theorem"], ["conditional_proof"], ["dafny"]),
    "git_delivery": AdapterDescriptor("git_delivery", "1", "builtin", ["software"], ["execution", "git_provenance"], ["git", "python"], False),
}


class AdapterRegistry:
    def __init__(self, *, load_plugins: bool = True) -> None:
        self._items: dict[str, Adapter] = {}
        self._descriptors: dict[str, AdapterDescriptor] = {}
        self.plugin_errors: list[str] = []
        for adapter in (DocumentAdapter(), PythonExecutionAdapter(), DiscoveryAdapter(), LeanAdapter(), DafnyAdapter(), GitDeliveryAdapter()):
            self.register(adapter, descriptor=_BUILTIN_DESCRIPTORS[adapter.name])
        if load_plugins:
            self.load_entry_points()

    def register(self, adapter: Adapter, *, descriptor: AdapterDescriptor | None = None) -> None:
        if not getattr(adapter, "name", None):
            raise ValueError("Adapter must expose a non-empty name")
        self._items[adapter.name] = adapter
        supplied = descriptor or getattr(adapter, "descriptor", None)
        self._descriptors[adapter.name] = supplied or AdapterDescriptor(name=adapter.name)

    def load_entry_points(self) -> None:
        try:
            entries = metadata.entry_points(group="nexus_u.adapters")
        except TypeError:
            entries = metadata.entry_points().get("nexus_u.adapters", ())
        for entry in entries:
            try:
                loaded = entry.load()
                adapter = loaded() if isinstance(loaded, type) else loaded
                self.register(adapter)
            except Exception as exc:
                self.plugin_errors.append(f"{entry.name}: {type(exc).__name__}: {exc}")

    def get(self, name: str) -> Adapter:
        try:
            return self._items[name]
        except KeyError as exc:
            raise KeyError(f"Unknown adapter: {name}. Available: {sorted(self._items)}") from exc

    def names(self) -> list[str]:
        return sorted(self._items)

    def descriptors(self) -> list[dict]:
        return [self._descriptors[name].to_dict() for name in sorted(self._descriptors)]
