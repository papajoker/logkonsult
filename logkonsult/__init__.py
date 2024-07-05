from importlib.metadata import version, PackageNotFoundError

__version__ = "."
try:
    __version__ = version("logKonsult")
except PackageNotFoundError:
    pass