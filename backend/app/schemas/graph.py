import uuid
from typing import Any

from pydantic import BaseModel


class KnowledgeNodeRead(BaseModel):
    # Constructed explicitly in the service layer (not model_validate'd straight off
    # the ORM row) since the ORM attribute is node_metadata -- see the comment in
    # app/db/models/graph.py for why -- and API consumers shouldn't need to know
    # about that internal naming workaround.
    id: uuid.UUID
    node_type: str
    label: str
    metadata: dict[str, Any]


class KnowledgeEdgeRead(BaseModel):
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    edge_type: str
    weight: float


class KnowledgeGraphResponse(BaseModel):
    nodes: list[KnowledgeNodeRead]
    edges: list[KnowledgeEdgeRead]


class CircularDependencyResponse(BaseModel):
    cycles: list[list[str]]

