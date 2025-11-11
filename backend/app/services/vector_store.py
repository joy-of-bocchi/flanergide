"""Vector database service using Chroma."""

import json
import logging
import time
import uuid
from typing import Optional

import chromadb

logger = logging.getLogger(__name__)


class VectorStore:
    """Chroma vector database for long-term memory."""

    def __init__(self, persist_dir: str):
        """Initialize Chroma client.

        Args:
            persist_dir: Directory for Chroma persistence
        """
        # Use PersistentClient for newer ChromaDB versions
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name="events",
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"Initialized Chroma at {persist_dir}")

    async def insert(self, event: dict, device_id: str) -> str:
        """Store a new event with automatic embedding.

        Args:
            event: Event dictionary with type, data, timestamp
            device_id: Device ID for metadata

        Returns:
            Event ID

        Raises:
            ValueError: If event is invalid
        """
        if not event.get("type"):
            raise ValueError("Event must have 'type'")

        # Generate human-readable text for embedding
        text = self._event_to_text(event)

        # Prepare metadata
        metadata = {
            "type": event.get("type", "unknown"),
            "device_id": device_id,
            "timestamp": event.get("timestamp", int(time.time()))
        }

        # Generate event ID
        event_id = str(uuid.uuid4())

        try:
            self.collection.add(
                documents=[text],
                metadatas=[metadata],
                ids=[event_id]
            )
            logger.info(f"Stored event {event_id} (type={event.get('type')})")
            return event_id
        except Exception as e:
            logger.error(f"Failed to insert event: {e}")
            raise

    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[dict] = None
    ) -> list[dict]:
        """Semantic search over stored events.

        Args:
            query: Search query
            limit: Number of results
            filters: Optional filters (type, timestamp range, etc.)

        Returns:
            List of matching events with similarity scores
        """
        try:
            # Build where filter if provided
            where = None
            if filters:
                where = self._build_where_filter(filters)

            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
                where=where,
                include=["documents", "metadatas", "distances"]
            )

            # Format results
            output = []
            if results and results["ids"] and len(results["ids"]) > 0:
                for i, doc_id in enumerate(results["ids"][0]):
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    output.append({
                        "id": doc_id,
                        "type": metadata.get("type", "unknown"),
                        "data": json.loads(results["documents"][0][i]) if isinstance(results["documents"][0][i], str) else {},
                        "timestamp": metadata.get("timestamp", 0),
                        "similarity_score": 1 - results["distances"][0][i]  # Convert distance to similarity
                    })

            logger.info(f"Search '{query[:50]}' returned {len(output)} results")
            return output

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    async def recent(
        self,
        limit: int = 20,
        offset: int = 0,
        type_filter: Optional[str] = None
    ) -> tuple[list[dict], int]:
        """Get recent events without semantic search.

        Args:
            limit: Number of results
            offset: Skip first N results
            type_filter: Optional event type filter

        Returns:
            Tuple of (results list, total count)
        """
        try:
            # Get all documents
            where = None
            if type_filter:
                where = {"type": {"$eq": type_filter}}

            all_results = self.collection.get(
                where=where,
                include=["documents", "metadatas"]
            )

            # Sort by timestamp (newest first)
            events = []
            if all_results and all_results["ids"]:
                for doc_id, metadata in zip(all_results["ids"], all_results["metadatas"]):
                    events.append({
                        "id": doc_id,
                        "type": metadata.get("type", "unknown"),
                        "timestamp": metadata.get("timestamp", 0),
                        "device_id": metadata.get("device_id", "unknown")
                    })

                events.sort(key=lambda x: x["timestamp"], reverse=True)

            # Apply pagination
            total = len(events)
            events = events[offset:offset + limit]

            logger.info(f"Retrieved {len(events)} recent events (offset={offset}, type={type_filter})")
            return events, total

        except Exception as e:
            logger.error(f"Failed to get recent events: {e}")
            raise

    async def delete(self, event_id: str) -> bool:
        """Delete an event from the database.

        Args:
            event_id: Event ID to delete

        Returns:
            True if deleted, False if not found

        Raises:
            Exception: If deletion fails
        """
        try:
            # Check if exists
            result = self.collection.get(ids=[event_id])
            if not result or not result["ids"]:
                logger.warning(f"Event {event_id} not found")
                return False

            # Delete
            self.collection.delete(ids=[event_id])
            logger.info(f"Deleted event {event_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete event {event_id}: {e}")
            raise

    def _event_to_text(self, event: dict) -> str:
        """Convert event to human-readable text for embedding.

        Args:
            event: Event dictionary

        Returns:
            Text representation
        """
        event_type = event.get("type", "unknown")
        data = event.get("data", {})

        if event_type == "app_launch":
            app = data.get("app", "unknown")
            duration = data.get("duration_seconds", 0)
            return f"App launch: {app} (duration: {duration} seconds)"

        elif event_type == "notification":
            source = data.get("source", "unknown")
            subject = data.get("subject", "")
            return f"Notification from {source}: {subject}"

        elif event_type == "minigame_complete":
            game_type = data.get("game_type", "unknown")
            success = data.get("success", False)
            status = "completed successfully" if success else "failed"
            return f"Mini-game {game_type} {status}"

        elif event_type == "user_interaction":
            action = data.get("action", "unknown")
            return f"User interaction: {action}"

        elif event_type == "avatar_mood_change":
            mood = data.get("mood", "unknown")
            return f"Avatar mood changed to {mood}"

        else:
            return f"{event_type}: {json.dumps(data)}"

    def _build_where_filter(self, filters: dict) -> Optional[dict]:
        """Build Chroma where filter from user filters.

        Args:
            filters: Filter dictionary (type, timestamp_min, timestamp_max)

        Returns:
            Chroma where filter or None
        """
        conditions = []

        if "type" in filters and filters["type"]:
            conditions.append({"type": {"$eq": filters["type"]}})

        if "timestamp_min" in filters and filters["timestamp_min"]:
            conditions.append({"timestamp": {"$gte": filters["timestamp_min"]}})

        if "timestamp_max" in filters and filters["timestamp_max"]:
            conditions.append({"timestamp": {"$lte": filters["timestamp_max"]}})

        if not conditions:
            return None

        if len(conditions) == 1:
            return conditions[0]

        return {"$and": conditions}

    def count(self) -> int:
        """Get total number of events in database.

        Returns:
            Total event count
        """
        return self.collection.count()
