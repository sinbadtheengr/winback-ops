"""Coordinate bounded demo code generation, verification, and repair."""
from __future__ import annotations

from datetime import date
import hashlib
import time

from app.agents.codegen import generate_demo_segmenter, repair_demo_segmenter
from app.api.datasets import get_dataset_path
from app.core.config import allow_unsafe_local_sandbox, is_demo_mode
from app.core.database import complete_run, create_run, get_profile, save_segmentation
from app.core.models import SegmentationResult
from app.sandbox.executor import SandboxError, execute


class SegmentationError(RuntimeError):
    pass


MAX_SANDBOX_ATTEMPTS = 3


def _verify_result(result: SegmentationResult) -> None:
    """Apply data-independent holdout checks to the generated output.

    The sandbox has already checked the strict JSON schema. These checks make
    sure its summary agrees with the client-level result and that a client does
    not appear in multiple segments. They are deliberately data-independent so
    a legitimate clinic with no dormant customers can still pass.
    """
    clients = [client for segment in result.segments for client in segment.clients]
    errors: list[str] = []
    if result.totals.get("dormant_clients") != len(clients):
        errors.append("total dormant_clients does not match the emitted client count")
    expected_revenue = round(sum(segment.recoverable_revenue for segment in result.segments), 2)
    if round(float(result.totals.get("recoverable_revenue", 0)), 2) != expected_revenue:
        errors.append("total recoverable_revenue does not match the emitted segment revenue")
    client_keys = [client.client_key for client in clients]
    if len(client_keys) != len(set(client_keys)):
        errors.append("a client appears in more than one segment")
    for client in clients:
        try:
            date.fromisoformat(client.last_visit)
        except ValueError:
            errors.append("a client has an invalid last_visit date")
            break
    if errors:
        raise SandboxError("Holdout verification failed: " + "; ".join(errors) + ".")


def segment_dataset(dataset_id: str) -> SegmentationResult:
    profile = get_profile(dataset_id)
    if profile is None:
        raise SegmentationError("Profile this dataset before segmentation.")
    if not is_demo_mode() and not allow_unsafe_local_sandbox():
        raise SegmentationError(
            "Live generated-code execution is disabled locally. Use an isolated RelayOps worker, "
            "or enable ALLOW_UNSAFE_LOCAL_SANDBOX=true only for controlled development."
        )
    try:
        csv_path = get_dataset_path(dataset_id)
    except FileNotFoundError as exc:
        raise SegmentationError("Dataset not found.") from exc
    error = ""
    for attempt in range(1, MAX_SANDBOX_ATTEMPTS + 1):
        if attempt == 1:
            source = generate_demo_segmenter(profile)
            agent_name, model = "codegen", "demo-codegen"
        else:
            source = repair_demo_segmenter(profile, error, attempt)
            agent_name, model = "codegen_repair", "demo-codegen-repair"
        source = source.replace("__CSV_PATH__", str(csv_path).replace("\\", "\\\\"))
        digest = hashlib.sha256(source.encode()).hexdigest()
        codegen_run = create_run(dataset_id=dataset_id, input_hash=digest, model=model, agent_name=agent_name)
        complete_run(codegen_run, status="completed", latency_ms=0, output=source)

        sandbox_run = create_run(dataset_id=dataset_id, input_hash=digest, model="sandbox", agent_name="sandbox")
        started = time.perf_counter()
        try:
            result = execute(source, csv_path)
            _verify_result(result)
        except SandboxError as exc:
            error = str(exc)
            complete_run(
                sandbox_run,
                status="failed",
                latency_ms=round((time.perf_counter() - started) * 1000),
                error=error,
            )
            continue
        complete_run(
            sandbox_run,
            status="completed",
            latency_ms=round((time.perf_counter() - started) * 1000),
            output=result.model_dump_json(),
        )
        save_segmentation(dataset_id, result.model_dump_json())
        return result
    raise SegmentationError(
        f"Sandbox verification failed after {MAX_SANDBOX_ATTEMPTS} attempts. Review Agent activity for the repair log."
    )
