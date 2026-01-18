"""
Conversation Memory for Document Retrieval Sessions

Persistent memory system for tracking conversation history,
enabling context-aware query rewriting and avoiding redundant searches.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
import hashlib


@dataclass
class ConversationTurn:
    """Represents a single conversation turn."""
    timestamp: str
    query: str
    optimized_query: Optional[str]
    results: List[Dict[str, Any]]
    documents_accessed: List[str]
    satisfaction_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConversationSession:
    """Represents a conversation session."""
    session_id: str
    created_at: str
    last_updated: str
    turns: List[ConversationTurn] = field(default_factory=list)
    context_summary: str = ""
    domain: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "turns": [t.to_dict() for t in self.turns],
            "context_summary": self.context_summary,
            "domain": self.domain
        }


class ConversationMemory:
    """
    Persistent conversation memory for document retrieval sessions.

    Features:
    - Store conversation history with results
    - Enable context-aware query rewriting
    - Detect continuation queries
    - Avoid redundant searches
    """

    def __init__(
        self,
        storage_dir: str = ".claude/memory",
        max_sessions: int = 100,
        max_turns_per_session: int = 50,
        debug_mode: bool = False
    ):
        """
        Initialize conversation memory.

        Args:
            storage_dir: Directory to store session data
            max_sessions: Maximum number of sessions to keep
            max_turns_per_session: Maximum turns per session
            debug_mode: Enable debug output
        """
        self.storage_dir = Path(storage_dir)
        self.max_sessions = max_sessions
        self.max_turns_per_session = max_turns_per_session
        self.debug_mode = debug_mode

        # Create storage directory if it doesn't exist
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Current session (loaded when set)
        self._current_session: Optional[ConversationSession] = None

    def create_session(
        self,
        session_id: Optional[str] = None,
        domain: Optional[str] = None
    ) -> ConversationSession:
        """
        Create a new conversation session.

        Args:
            session_id: Optional session ID (auto-generated if None)
            domain: Optional domain/topic for the session

        Returns:
            New ConversationSession
        """
        if session_id is None:
            session_id = self._generate_session_id()

        now = datetime.now().isoformat()

        session = ConversationSession(
            session_id=session_id,
            created_at=now,
            last_updated=now,
            domain=domain
        )

        self._current_session = session
        self._save_session(session)

        self._debug_print(f"Created new session: {session_id}")

        return session

    def load_session(self, session_id: str) -> Optional[ConversationSession]:
        """
        Load an existing session.

        Args:
            session_id: Session ID to load

        Returns:
            ConversationSession if found, None otherwise
        """
        session_path = self.storage_dir / f"{session_id}.json"

        if not session_path.exists():
            self._debug_print(f"Session not found: {session_id}")
            return None

        try:
            with open(session_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Reconstruct turns
            turns = [
                ConversationTurn(**t) for t in data.get("turns", [])
            ]

            session = ConversationSession(
                session_id=data["session_id"],
                created_at=data["created_at"],
                last_updated=data["last_updated"],
                turns=turns,
                context_summary=data.get("context_summary", ""),
                domain=data.get("domain")
            )

            self._current_session = session

            self._debug_print(f"Loaded session: {session_id} ({len(turns)} turns)")

            return session

        except Exception as e:
            self._debug_print(f"Error loading session: {e}")
            return None

    def add_turn(
        self,
        query: str,
        optimized_query: Optional[str],
        results: List[Dict[str, Any]],
        satisfaction_score: Optional[float] = None
    ) -> None:
        """
        Add a conversation turn to the current session.

        Args:
            query: Original user query
            optimized_query: Optimized query (if any)
            results: Search results from the query
            satisfaction_score: Optional satisfaction score (0-1)
        """
        if self._current_session is None:
            # Create a new session automatically
            self.create_session()

        # Extract document titles from results
        documents_accessed = [
            r.get("title", "") for r in results if r.get("title")
        ]

        turn = ConversationTurn(
            timestamp=datetime.now().isoformat(),
            query=query,
            optimized_query=optimized_query,
            results=results,
            documents_accessed=documents_accessed,
            satisfaction_score=satisfaction_score
        )

        self._current_session.turns.append(turn)
        self._current_session.last_updated = datetime.now().isoformat()

        # Update context summary
        self._update_context_summary()

        # Trim if exceeding max turns
        if len(self._current_session.turns) > self.max_turns_per_session:
            self._current_session.turns = self._current_session.turns[-self.max_turns_per_session:]

        # Save session
        self._save_session(self._current_session)

        self._debug_print(f"Added turn to session: {self._current_session.session_id}")

    def get_context_for_query(self, query: str) -> Dict[str, Any]:
        """
        Get relevant context for a new query.

        Args:
            query: The new query

        Returns:
            Context dictionary with:
                - previous_queries: Recent queries
                - domain: Inferred domain
                - suggested_rewrites: Contextually optimized query
                - documents_to_skip: Documents already accessed
        """
        if self._current_session is None or not self._current_session.turns:
            return {
                "previous_queries": [],
                "domain": None,
                "suggested_rewrites": None,
                "documents_to_skip": []
            }

        recent_turns = self._current_session.turns[-3:]  # Last 3 turns
        domain = self._current_session.domain

        context = {
            "previous_queries": [t.query for t in recent_turns],
            "domain": domain,
            "suggested_rewrites": None,
            "documents_to_skip": []
        }

        # Check if this is a continuation query
        continuation = self._detect_continuation(query)
        if continuation:
            context["suggested_rewrites"] = continuation

        # Get documents already accessed (to avoid redundant retrieval)
        all_accessed: set[str] = set()
        for turn in self._current_session.turns:
            all_accessed.update(turn.documents_accessed)

        context["documents_to_skip"] = list(all_accessed)

        return context

    def _detect_continuation(self, query: str, domain: Optional[str] = None) -> Optional[str]:
        """
        Detect if query is a continuation and suggest rewrite.

        Args:
            query: The query to check
            domain: Optional domain context from session

        Examples:
        - "那 X 呢？" → "X"
        - "And Y?" → "Y"
        - "What about Z?" → "Z"
        """
        query_lower = query.lower().strip()

        # Chinese continuation patterns
        cn_patterns = [
            (r'^(那|那么|然后)(.+呢)?[？?]?$', 2),  # "那X呢？", "那呢？"
            (r'^(另外|还有)(.+)?$', 2),  # "另外X", "还有呢？"
        ]

        # English continuation patterns
        en_patterns = [
            (r'^(and|or)(.+)?$', 2),  # "and X", "or?"
            (r'^(what about|how about)(.+)?$', 2),  # "what about X"
        ]

        all_patterns = cn_patterns + en_patterns

        for pattern, group_idx in all_patterns:
            match = re.match(pattern, query_lower, re.IGNORECASE)
            if match:
                # Extract the continuation topic
                topic = match.group(group_idx) if match.group(group_idx) else ""

                # If no topic, use domain from context
                if not topic and domain:
                    return f"{domain} information"

                # Return suggested rewrite
                if topic:
                    return topic.strip()

        return None

    def _update_context_summary(self) -> None:
        """Update the context summary based on recent turns."""
        if self._current_session is None or not self._current_session.turns:
            return

        # Get recent queries
        recent_queries = [t.query for t in self._current_session.turns[-5:]]

        # Extract key terms
        key_terms: set = set()
        for query in recent_queries:
            # Simple keyword extraction
            words = query.split()
            key_terms.update(w for w in words if len(w) > 3)

        # Infer domain if not set
        if not self._current_session.domain:
            self._current_session.domain = self._infer_domain(recent_queries)

        # Build summary
        summary = f"Session with {len(self._current_session.turns)} turns. "
        summary += f"Topics: {', '.join(list(key_terms)[:5])}. "

        if self._current_session.domain:
            summary += f"Domain: {self._current_session.domain}."

        self._current_session.context_summary = summary

    def _infer_domain(self, queries: List[str]) -> Optional[str]:
        """Infer domain from query history."""
        # Common domain keywords
        domain_keywords = {
            "claude": ["claude", "claude code", "anthropic"],
            "python": ["python", "pip", "pypi"],
            "react": ["react", "reactjs", "jsx"],
            "javascript": ["javascript", "js", "node"],
        }

        # Count domain mentions
        domain_scores = {domain: 0 for domain in domain_keywords}

        for query in queries:
            query_lower = query.lower()
            for domain, keywords in domain_keywords.items():
                if any(kw in query_lower for kw in keywords):
                    domain_scores[domain] += 1

        # Return domain with highest score
        max_score = max(domain_scores.values())
        if max_score > 0:
            for domain, score in domain_scores.items():
                if score == max_score:
                    return domain

        return None

    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_hash = hashlib.md5(os.urandom(8)).hexdigest()[:8]
        return f"session_{timestamp}_{random_hash}"

    def _save_session(self, session: ConversationSession) -> None:
        """Save session to disk."""
        session_path = self.storage_dir / f"{session.session_id}.json"

        try:
            with open(session_path, 'w', encoding='utf-8') as f:
                json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            self._debug_print(f"Error saving session: {e}")

    def list_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List available sessions.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of session summaries
        """
        sessions = []

        for session_file in self.storage_dir.glob("*.json"):
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                sessions.append({
                    "session_id": data["session_id"],
                    "created_at": data["created_at"],
                    "last_updated": data["last_updated"],
                    "num_turns": len(data.get("turns", [])),
                    "domain": data.get("domain")
                })
            except Exception:
                continue

        # Sort by last updated
        sessions.sort(key=lambda s: s["last_updated"], reverse=True)

        return sessions[:limit]

    def cleanup_old_sessions(self, keep_last_n: Optional[int] = None) -> int:
        """
        Clean up old sessions.

        Args:
            keep_last_n: Number of recent sessions to keep (defaults to max_sessions)

        Returns:
            Number of sessions deleted
        """
        keep_last_n = keep_last_n if keep_last_n is not None else self.max_sessions

        sessions = self.list_sessions(limit=self.max_sessions * 2)

        if len(sessions) <= keep_last_n:
            return 0

        # Delete old sessions
        deleted = 0
        for session in sessions[keep_last_n:]:
            session_path = self.storage_dir / f"{session['session_id']}.json"
            try:
                session_path.unlink()
                deleted += 1
            except Exception:
                continue

        self._debug_print(f"Cleaned up {deleted} old sessions")

        return deleted

    @property
    def current_session(self) -> Optional[ConversationSession]:
        """Get the current session."""
        return self._current_session

    def _debug_print(self, msg: str):
        if self.debug_mode:
            print(f"[ConversationMemory] {msg}")


import re  # Import re here for _detect_continuation


# Convenience function for quick usage
def create_memory(
    storage_dir: str = ".claude/memory",
    session_id: Optional[str] = None
) -> ConversationMemory:
    """
    Create a new conversation memory instance.

    Args:
        storage_dir: Directory to store session data
        session_id: Optional session ID to load (creates new if None)

    Returns:
        ConversationMemory instance with session loaded/created

    Example:
        >>> memory = create_memory()
        >>> memory.add_turn("hooks configuration", None, results)
        >>> context = memory.get_context_for_query("那部署呢？")
    """
    memory = ConversationMemory(storage_dir=storage_dir)

    if session_id:
        memory.load_session(session_id)
    else:
        memory.create_session()

    return memory
