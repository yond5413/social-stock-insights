"""
Background tasks helper for FastAPI BackgroundTasks integration.

This module provides wrapper functions to trigger background processing
from API endpoints using FastAPI's BackgroundTasks.
"""

import asyncio
import logging
from typing import Optional

from fastapi import BackgroundTasks

from .scheduler import process_post

logger = logging.getLogger(__name__)


async def _run_process_post(post_id: str) -> None:
    """
    Internal wrapper to run process_post in the background.
    Handles any uncaught exceptions to prevent task crashes.
    """
    try:
        await process_post(post_id)
    except Exception as e:
        logger.error(f"Background task failed for post {post_id}: {str(e)}")


def enqueue_post_processing(background_tasks: BackgroundTasks, post_id: str) -> None:
    """
    Enqueue a post for background LLM processing using FastAPI BackgroundTasks.
    
    Use this function in API endpoints after creating a new post:
    
    Example:
        @router.post("/create")
        async def create_post(
            post: PostCreate,
            background_tasks: BackgroundTasks
        ):
            # ... create post in database ...
            enqueue_post_processing(background_tasks, post_id)
            return {"id": post_id, "status": "processing"}
    
    Args:
        background_tasks: FastAPI BackgroundTasks dependency
        post_id: The ID of the post to process
    """
    background_tasks.add_task(_run_process_post, post_id)
    logger.info(f"Enqueued post {post_id} for background processing")


def trigger_post_processing(post_id: str) -> None:
    """
    Trigger post processing using asyncio.create_task.
    
    Use this when you don't have access to FastAPI BackgroundTasks,
    such as in scheduled jobs or standalone scripts.
    
    Args:
        post_id: The ID of the post to process
    """
    asyncio.create_task(_run_process_post(post_id))
    logger.info(f"Triggered background processing for post {post_id}")


async def process_post_sync(post_id: str, timeout: Optional[float] = 30.0) -> bool:
    """
    Process a post synchronously with optional timeout.
    
    Use this when you need to wait for processing to complete,
    such as in tests or admin endpoints.
    
    Args:
        post_id: The ID of the post to process
        timeout: Maximum time to wait in seconds (None for no timeout)
    
    Returns:
        True if processing completed successfully, False otherwise
    """
    try:
        if timeout:
            await asyncio.wait_for(process_post(post_id), timeout=timeout)
        else:
            await process_post(post_id)
        return True
    except asyncio.TimeoutError:
        logger.warning(f"Processing post {post_id} timed out after {timeout}s")
        return False
    except Exception as e:
        logger.error(f"Error processing post {post_id} synchronously: {str(e)}")
        return False

