#!/usr/bin/env python3
"""
AgentCore Memory integration library.
Provides a clean Python API for memory operations.
Generic version for CaaS instances — reads config from .memory-id file.
"""

import sys
sys.path.insert(0, '/home/ssm-user/.openclaw/lib/python')

import logging
from typing import List, Dict, Optional
from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.memory.session import MemorySessionManager

MEMORY_ID_FILE = "/home/ssm-user/.openclaw/workspace/agentcore-memory/.memory-id"
REGION = "us-west-2"
DEFAULT_ACTOR_ID = "owner"

logger = logging.getLogger(__name__)


class RexMemory:
    """AgentCore Memory integration"""

    def __init__(self, memory_id: Optional[str] = None, region: str = REGION,
                 actor_id: str = DEFAULT_ACTOR_ID):
        self.region = region
        self.actor_id = actor_id
        self.client = MemoryClient(region_name=region)

        if memory_id is None:
            try:
                with open(MEMORY_ID_FILE, 'r') as f:
                    memory_id = f.read().strip()
            except FileNotFoundError:
                raise ValueError(f"No memory_id provided and {MEMORY_ID_FILE} not found.")

        self.memory_id = memory_id
        self.session_manager = MemorySessionManager(memory_id=memory_id, region_name=region)
        logger.info("RexMemory initialized: memory_id=%s, region=%s, actor=%s",
                     memory_id, region, actor_id)

    def log_turn(self, user_message: str, assistant_message: str,
                 actor_id: str = None, session_id: str = None) -> Dict:
        actor_id = actor_id or self.actor_id
        if session_id is None:
            from datetime import datetime
            session_id = f"session-{datetime.now().strftime('%Y%m%d')}"

        event = self.client.create_event(
            memory_id=self.memory_id,
            actor_id=actor_id,
            session_id=session_id,
            messages=[(user_message, "USER"), (assistant_message, "ASSISTANT")]
        )
        logger.info("Logged conversation turn to session %s", session_id)
        return event

    def search_memories(self, query: str, namespace: str = None, top_k: int = 5) -> List[Dict]:
        if namespace is None:
            namespace = f"/claw/{self.actor_id}/"
        results = self.client.retrieve_memories(
            memory_id=self.memory_id, namespace=namespace, query=query, top_k=top_k
        )
        return results

    def get_memory_info(self) -> Dict:
        response = self.client.gmcp_client.get_memory(memoryId=self.memory_id)
        memory = response.get('memory', response)
        return {
            'id': memory.get('id') or memory.get('memoryId'),
            'name': memory.get('name'),
            'status': memory.get('status'),
        }


def get_rex_memory() -> RexMemory:
    return RexMemory()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        mem = RexMemory()
        print(f"Memory loaded: {mem.memory_id}")
        info = mem.get_memory_info()
        for k, v in info.items():
            print(f"  {k}: {v}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
