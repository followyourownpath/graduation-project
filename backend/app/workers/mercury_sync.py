import os
import sys
import time
import logging
from datetime import datetime, timedelta, timezone

# Add parent directory to path so we can import app modules properly
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.config import Config
from app.integrations.mercury.client import MercuryClient
from app.integrations.mercury.extension_merge import ExtensionMerger
from app.integrations.mercury.sync_service import MercurySyncService
from app.services.crm_repository import SupabaseCrmRepository

# Configure logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("mercury_worker")


def calculate_backoff_seconds(attempt: int) -> int:
    """Calculates exponential backoff delay in seconds: 5s, 15s, 45s, 135s (2.25m), 405s (6.75m)."""
    return 5 * (3 ** (attempt - 1))


def run_worker():
    logger.info("Initializing Mercury CRM Sync Worker...")

    if not Config.MERCURY_ENABLED:
        logger.warning("MERCURY_ENABLED is False in config. Worker will exit.")
        return

    if not Config.SUPABASE_URL or not Config.SUPABASE_SECRET_KEY:
        logger.error("SUPABASE_URL and SUPABASE_SECRET_KEY must be configured. Worker exiting.")
        return

    # 1. Initialize Supabase Repository (using secret service role key to bypass RLS)
    repository = SupabaseCrmRepository(
        Config.SUPABASE_URL,
        Config.SUPABASE_SECRET_KEY,
        timeout_seconds=20.0
    )

    # 2. Initialize Mercury Client
    client = MercuryClient(
        base_url=Config.MERCURY_BASE_URL,
        token=Config.MERCURY_API_TOKEN,
        api_key=Config.MERCURY_API_KEY,
        timeout_seconds=Config.MERCURY_TIMEOUT_SECONDS,
        allow_writes=Config.MERCURY_ALLOW_WRITES,
        dry_run=Config.MERCURY_DRY_RUN,
        test_record_prefix=Config.MERCURY_TEST_RECORD_PREFIX
    )

    merger = ExtensionMerger(client)
    sync_service = MercurySyncService(client, merger, repository)

    poll_interval = Config.MERCURY_WORKER_POLL_SECONDS
    logger.info(f"Worker initialized. Starting poll loop (interval: {poll_interval}s).")
    logger.info(f"Configuration: DRY_RUN={client.dry_run}, ALLOW_WRITES={client.allow_writes}")

    while True:
        try:
            # Query pending or failed_retryable tracking jobs
            pending_jobs = repository.get_pending_trackings()

            for job in pending_jobs:
                job_id = job["id"]
                attempt = job.get("attempt_count", 0)
                status = job.get("update_status")

                # If job is failed_retryable, check backoff delay
                # Fetch next_attempt_at if it's there
                next_attempt = job.get("next_attempt_at")
                if next_attempt and status == "failed_retryable":
                    # Convert next_attempt timestamp to datetime object
                    try:
                        next_dt = datetime.fromisoformat(next_attempt.replace("Z", "+00:00"))
                        if datetime.now(timezone.utc) < next_dt:
                            # Skip for now
                            continue
                    except Exception as e:
                        logger.warning(f"Could not parse next_attempt_at '{next_attempt}': {e}")

                logger.info(f"Starting execution of tracking job {job_id} (Attempt {attempt + 1})...")

                # Mark job as in_progress in DB
                repository.update_tracking(
                    job_id,
                    {
                        "update_status": "in_progress",
                        "started_at": datetime.now(timezone.utc).isoformat(),
                    }
                )

                try:
                    # Run sync
                    sync_service.sync_tracking_job(job_id)
                    logger.info(f"Successfully finished tracking job {job_id}.")

                except Exception as e:
                    # Sync service updates DB status, but we must calculate backoff and retries here
                    new_attempt = attempt + 1
                    logger.error(f"Error executing tracking job {job_id}: {str(e)}")

                    # Read latest status to see if it was marked permanent or retryable
                    # (sync_service updates it)
                    latest_job = repository.get_tracking(job_id)
                    latest_status = latest_job.get("update_status") if latest_job else "failed_retryable"

                    if latest_status == "failed_retryable":
                        if new_attempt >= Config.MERCURY_MAX_ATTEMPTS:
                            # Mark as permanently failed if max attempts reached
                            logger.error(f"Job {job_id} reached max retry attempts ({Config.MERCURY_MAX_ATTEMPTS}). Marking as failed_permanent.")
                            repository.update_tracking(
                                job_id,
                                {
                                    "update_status": "failed_permanent",
                                    "attempt_count": new_attempt,
                                    "last_error_message": f"Reached max retry attempts. Last error: {str(e)}",
                                }
                            )
                            # Set local sync status to failed
                            repository.update_local_ids_and_sync_status(
                                latest_job["fact_find_submission_id"],
                                latest_job["crm_application_id"],
                                "",
                                "failed"
                            )
                        else:
                            # Calculate next retry timestamp
                            delay_sec = calculate_backoff_seconds(new_attempt)
                            next_dt = datetime.now(timezone.utc) + timedelta(seconds=delay_sec)
                            logger.info(f"Scheduling retry {new_attempt + 1} for job {job_id} at {next_dt.isoformat()} (delay: {delay_sec}s)")
                            
                            repository.update_tracking(
                                job_id,
                                {
                                    "attempt_count": new_attempt,
                                    "next_attempt_at": next_dt.isoformat(),
                                }
                            )

                    elif latest_status == "failed_permanent":
                        logger.error(f"Job {job_id} encountered a permanent error. No retries will be made.")
                        repository.update_tracking(
                            job_id,
                            {
                                "attempt_count": new_attempt,
                            }
                        )

        except Exception as e:
            logger.error(f"Worker encounter error in main loop: {e}")

        # Sleep before next poll
        time.sleep(poll_interval)


if __name__ == "__main__":
    try:
        run_worker()
    except KeyboardInterrupt:
        logger.info("Worker stopped by user.")
        sys.exit(0)
