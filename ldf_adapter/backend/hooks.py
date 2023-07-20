import os
import subprocess

from ldf_adapter.logsetup import logger


class Hooks:
    def __init__(self, **hooks):
        for k, v in hooks.items():
            setattr(self, k, v)
            logger.debug(f"Hook {k} set to {v}")

    def execute(self, hook, *hook_args):
        if not hasattr(self, hook):
            logger.error(f"Hook '{hook}' not implemented")
            return

        hook_script = getattr(self, hook)
        logger.debug(f"Executing hook for {hook}: {hook_script}")

        if not os.path.isfile(hook_script):
            logger.error(f"Hook for {hook}: {hook_script} does not exist, skipping.")
            return
        command = [hook_script, *hook_args]
        if hook_script.endswith(".sh"):
            command.insert(0, "bash")
        elif hook_script.endswith(".py"):
            command.insert(0, "python3")
        else:
            logger.error(
                f"Hook for {hook}: {hook_script} is not a bash or python script, skipping."
            )
            return
        try:
            logger.info(f"Running hook for {hook}: {hook_script}")
            subprocess.run(
                command,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError as e:
            logger.error(
                f"Error running hook for {hook}: {hook_script}: {e}. Skipping."
            )
            return
