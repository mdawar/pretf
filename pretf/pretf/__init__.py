import errno
import json
import os
import shlex
import sys
from glob import glob
from pathlib import Path

from . import log

__version__ = "0.0.1"


class tf:
    """
    Creates a Terraform block to output as JSON.

    """

    def __init__(self, name, data):
        self.__name = name
        self.__data = data

    def __iter__(self):
        result = {}
        here = result
        for part in self.__name.split("."):
            here[part] = {}
            here = here[part]
        here.update(self.__data)
        return iter(result.items())

    def __getattr__(self, attr):

        parts = self.__name.split(".")

        if parts[0] == "resource":
            parts.pop(0)
        elif parts[0] == "variable":
            parts[0] = "var"

        parts.append(attr)

        return "${" + ".".join(parts) + "}"

    def __str__(self):
        return self.__name


def _get_terraform_blocks(func, kwargs):
    result = func(**kwargs)
    if hasattr(result, "__next__") and hasattr(result, "send"):
        block = next(result)
        yield block
        while True:
            try:
                block = result.send(block)
                yield block
            except StopIteration:
                break
    else:
        yield from result


def _load_functions(paths):
    for path in paths:
        sys.path.insert(0, path)
        try:
            for name in os.listdir(path):
                if name.endswith(".tf.py"):
                    global_scope = {}
                    with open(os.path.join(path, name)) as open_file:
                        exec(open_file.read(), global_scope)
                    yield (name[:-6], global_scope["terraform"])
        finally:
            sys.path.pop(0)
    return []


def _render_function(func, kwargs):
    contents = []
    for block in _get_terraform_blocks(func, kwargs):
        if isinstance(block, tf):
            data = dict(iter(block))
        else:
            data = block
        contents.append(data)
    return contents


def create(*_paths, **_kwargs):
    result = []
    for name, func in _load_functions(_paths or ["."]):

        # Render the Terraform blocks.
        contents = _render_function(func, _kwargs)

        # Write JSON file.
        output_name = f"{name}.tf.json"
        with open(output_name, "w") as open_file:
            json.dump(contents, open_file, indent=2)

        log.ok(f"create: {output_name}")
        result.append(output_name)

    return result


def execute(file, args=None, default_args=None, env=None, verbose=True):
    """
    Executes a command and waits for it to finish.

    If args are provided, then they will be used.

    If args are not provided, and arguments were used to run this program,
    then those arguments will be used.

    If args are not provided, and no arguments were used to run this program,
    and default args are provided, then they will be used.

    """

    if args is not None:
        args = [file] + args
    else:
        if sys.argv[1:]:
            args = [file] + sys.argv[1:]
        elif default_args:
            args = [file] + default_args
        else:
            args = [file]

    if verbose:
        log.ok(f"run: {' '.join(shlex.quote(arg) for arg in args)}")

    if env is None:
        env = os.environ

    child_pid = os.fork()
    if child_pid == 0:
        os.execvpe(file, args, env)
    else:
        while True:
            try:
                _, exit_status = os.waitpid(child_pid, 0)
            except KeyboardInterrupt:
                pass
            except OSError as error:
                if error.errno == errno.ECHILD:
                    # No child processes.
                    # It has exited already.
                    break
                elif error.errno == errno.EINTR:
                    # Interrupted system call.
                    # This happens when resizing the terminal.
                    pass
                else:
                    # An actual error occurred.
                    raise
            else:
                exit_code = exit_status >> 8
                return exit_code


def mirror(*sources, target="."):
    """
    Creates symlinks from all files and directories in the source
    directories into the target directory. Deletes all existing
    symlinks in the target directory.

    """

    target_path = Path(target)

    # Delete old symlinks in target path.
    for target_file_path in target_path.iterdir():
        if target_file_path.is_symlink():
            target_file_path.unlink()

    # Create new symlinks from source paths.
    for source in sources:
        if target == ".":
            log.ok(f"mirror: {source}")
        else:
            log.ok(f"mirror: {source} to {target}")
        source_path = Path(source)
        for source_file_path in source_path.iterdir():
            target_file_path = target_path / source_file_path.name
            target_file_path.symlink_to(source_file_path)


def remove(*patterns, exclude=None):

    old_paths = set()
    for pattern in patterns:
        old_paths.update(glob(pattern))

    if isinstance(exclude, str):
        exclude = [exclude]

    if exclude:
        for path in exclude:
            old_paths.discard(path)

    for path in old_paths:
        log.ok(f"remove: {path}")
        os.remove(path)
