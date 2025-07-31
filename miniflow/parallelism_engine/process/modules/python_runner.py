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

        # Get context (task parameters)
        context = item.get("context", {})
        if isinstance(context, str):
            context = json.loads(context)

        # Create task_data payload for the script
        task_data = {
            "node_id": item.get("node_id"),
            "node_name": item.get("node_name"), 
            "execution_id": item.get("execution_id"),
            "workflow_id": item.get("workflow_id"),
            "node_params": context  # Parameters passed to the script
        }

        # Execute using pure functional patterns only (optimal for Miniflow)
        result = None
        
        # Pattern 1: Modern main(task_data) function (PREFERRED - RECOMMENDED)
        if hasattr(module, "main"):
            result = module.main(task_data)
            
        # Pattern 2: Simple run(context) function (LIGHTWEIGHT ALTERNATIVE)
        elif hasattr(module, "run"):
            result = module.run(context)
            
        else:
            raise AttributeError(
                "Script must contain one of:\n"
                "  • main(task_data) [RECOMMENDED] - Full task context with metadata\n"
                "  • run(context) [SIMPLE] - Minimal overhead with just parameters\n"
                "\n"
                "✅ Both patterns are pure functional (stateless, thread-safe)\n"
                "❌ OOP patterns removed for optimal multiprocessing performance"
            )

        # Handle result processing
        if result is None:
            result = {"status": "completed", "message": "No return value"}
            
        # If result is string, try to parse as JSON
        if isinstance(result, str):
            try:
                parsed_output = json.loads(result)
            except json.JSONDecodeError:
                # If not valid JSON, wrap the string
                parsed_output = {"output": result}
        else:
            # If result is already dict/object, use it directly
            parsed_output = result

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
