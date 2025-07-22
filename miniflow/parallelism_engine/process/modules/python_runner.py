import importlib.util
import json
from queue import Queue


def python_runner(item: json, output_queue: Queue):
    try:
        script_path = item.get("script_path")
        if not script_path:
            raise ValueError("script_path is missing")

        module_name = script_path.split("/")[-1].replace(".py", "")

        spec = importlib.util.spec_from_file_location(module_name, script_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load spec for module at {script_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if not hasattr(module, "module"):
            raise AttributeError("The module must contain a 'module()' function")

        run_module = module.module()

        if not hasattr(run_module, "run"):
            raise AttributeError("The object returned by 'module()' must have a 'run()' method")

        context = item.get("context")

        if isinstance(context, str):
            context = json.loads(context)



        result = run_module.run(context)

        parsed_output = json.loads(result)
        item["result_data"] = parsed_output
        item["status"] = "success"

    except FileNotFoundError:
        item["error_message"] = "Script file not found"
        item["status"] = "failed"
    except ImportError as e:
        item["error_message"] = f"Import error: {str(e)}"
        item["status"] = "failed"
    except AttributeError as e:
        item["error_message"] = f"Attribute error: {str(e)}"
        item["status"] = "failed"
    except ValueError as e:
        item["error_message"] = f"Value error: {str(e)}"
        item["status"] = "failed"
    except (json.JSONDecodeError, TypeError) as e:
        item["error_message"] = f"JSON error: {str(e)}"
        item["status"] = "failed"
    except Exception as e:
        item["error_message"] = f"Unexpected error: {str(e)}"
        item["status"] = "failed"

    output_queue.put(item)
