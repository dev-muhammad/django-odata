"""
Circular dependency detector for SPECKIT-008: Auto-Generate OData Serializers.

This module provides utilities to detect and resolve circular dependencies
in model relationships using graph-based cycle detection (DFS algorithm).
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple


@dataclass
class ModelGraph:
    """Directed graph of model relationships."""

    nodes: Set[str] = field(default_factory=set)  # Set of model paths (app.Model)
    edges: Dict[str, Set[str]] = field(
        default_factory=lambda: defaultdict(set)
    )  # model -> set of related models


@dataclass
class CircularDependency:
    """Information about a circular dependency."""

    cycle: List[str]  # List of models in the cycle
    edge_to_skip: Tuple[str, str]  # (from_model, to_model) to break cycle


def build_relationship_graph(models: List[type], relationships_map: Dict) -> ModelGraph:
    """
    Build a directed graph of model relationships.

    Args:
        models: List of Django model classes
        relationships_map: Dict mapping model paths to their relationships

    Returns:
        ModelGraph object representing the relationship graph
    """
    graph = ModelGraph()

    # Add nodes
    for model in models:
        model_path = f"{model._meta.app_label}.{model.__name__}"
        graph.nodes.add(model_path)

    # Add edges (relationships)
    for model_path, relationships in relationships_map.items():
        for relationship in relationships:
            graph.edges[model_path].add(relationship.related_model)

    return graph


def detect_cycles(graph: ModelGraph) -> List[CircularDependency]:
    """
    Detect cycles in the relationship graph using DFS.

    Args:
        graph: ModelGraph object

    Returns:
        List of CircularDependency objects
    """
    visited = set()
    rec_stack = set()
    cycles = []

    def dfs(node: str, path: List[str]) -> None:
        """Depth-first search to detect cycles."""
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.edges.get(node, set()):
            if neighbor not in visited:
                dfs(neighbor, path[:])
            elif neighbor in rec_stack:
                # Cycle detected
                cycle_start_idx = path.index(neighbor)
                cycle = path[cycle_start_idx:] + [neighbor]
                # Edge to skip is from current node to neighbor
                edge_to_skip = (node, neighbor)
                cycles.append(
                    CircularDependency(cycle=cycle, edge_to_skip=edge_to_skip)
                )

        rec_stack.discard(node)

    # Run DFS from each unvisited node
    for node in graph.nodes:
        if node not in visited:
            dfs(node, [])

    return cycles


def resolve_circular_dependencies(
    cycles: List[CircularDependency],
) -> Set[Tuple[str, str]]:
    """
    Resolve circular dependencies by identifying edges to skip.

    Strategy: Skip reverse relationships to break cycles, prioritizing
    forward relationships (FK, M2M, O2O).

    Args:
        cycles: List of CircularDependency objects

    Returns:
        Set of edges (from_model, to_model) to exclude from expandable_fields
    """
    edges_to_skip = set()

    for cycle in cycles:
        # For each cycle, we skip the edge identified by the algorithm
        edges_to_skip.add(cycle.edge_to_skip)

    return edges_to_skip


def should_include_relationship(
    from_model: str, to_model: str, excluded_edges: Set[Tuple[str, str]]
) -> bool:
    """
    Determine if a relationship should be included in expandable_fields.

    Args:
        from_model: Source model path
        to_model: Target model path
        excluded_edges: Set of edges to exclude

    Returns:
        True if relationship should be included, False otherwise
    """
    return (from_model, to_model) not in excluded_edges
