"""Modul-Registry: Registriert und verwaltet alle verfügbaren Module."""

from core.base_module import BaseModule

_modules: dict[str, BaseModule] = {}


def register(module: BaseModule) -> None:
    _modules[module.name] = module


def get_module(name: str) -> BaseModule:
    if name not in _modules:
        raise KeyError(f"Modul '{name}' nicht registriert. Verfügbar: {list(_modules.keys())}")
    return _modules[name]


def list_modules() -> list[str]:
    return list(_modules.keys())


def all_modules() -> dict[str, BaseModule]:
    return dict(_modules)
