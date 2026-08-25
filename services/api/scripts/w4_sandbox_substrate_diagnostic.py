from __future__ import annotations

import inspect
import json
import os

from vercel.api import session
from vercel.sandbox import NetworkPolicy
from vercel.sandbox import sync as sandbox


def _signature(value: object) -> str | None:
    try:
        return str(inspect.signature(value))
    except (TypeError, ValueError):
        return None


def main() -> None:
    project_id = (os.getenv("VERCEL_PROJECT_ID") or "").strip()
    if not project_id:
        raise RuntimeError("sandbox diagnostic requires Vercel project identity")

    module_snapshot_members = sorted(name for name in dir(sandbox) if "snapshot" in name.casefold())
    output: dict[str, object] = {
        "create_sandbox_signature": _signature(sandbox.create_sandbox),
        "module_snapshot_members": module_snapshot_members,
    }

    with session():
        with sandbox.create_sandbox(
            project_id=project_id,
            execution_time_limit=90,
            persistent=False,
            network_policy=NetworkPolicy.deny_all(),
            env={},
            destroy=True,
            tags={"parallax": "offline-substrate-diagnostic"},
        ) as instance:
            instance_snapshot_members = sorted(name for name in dir(instance) if "snapshot" in name.casefold())
            output["instance_snapshot_members"] = instance_snapshot_members
            output["instance_snapshot_signatures"] = {
                name: _signature(getattr(instance, name)) for name in instance_snapshot_members
            }
            result = instance.run_process(
                "python",
                [
                    "-c",
                    (
                        "import importlib.util,json,os,shutil,sys;"
                        "print(json.dumps({"
                        "'cwd':os.getcwd(),"
                        "'python':sys.version.split()[0],"
                        "'pytest':importlib.util.find_spec('pytest') is not None,"
                        "'pip_module':importlib.util.find_spec('pip') is not None,"
                        "'pip_bin':shutil.which('pip'),"
                        "'uv_bin':shutil.which('uv'),"
                        "'python_bin':shutil.which('python')"
                        "},sort_keys=True))"
                    ),
                ],
                env={},
                kill_after=60,
                capture_output=True,
            )
            output["sandbox_probe"] = {
                "exit_code": result.returncode,
                "stdout": (result.stdout or "")[:1000],
                "stderr": (result.stderr or "")[:1000],
            }

    print(json.dumps(output, indent=2, sort_keys=True))
    raise RuntimeError("offline sandbox substrate diagnostic stops intentionally")


if __name__ == "__main__":
    main()
