#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database connection and helper functions
"""

import os
import sqlite3
from contextlib import contextmanager
from typing import Dict, List, Tuple
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DB_PATH = os.getenv("DB_PATH", "./geo_points.db")
T_PLACES = os.getenv("TABLE_PLACES", "places")
T_REL = os.getenv("TABLE_RELATIONS", "relations")
T_DYNA = os.getenv("TABLE_DYNA", "dyna")


def _connect() -> sqlite3.Connection:
    """Create a database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()


def load_nodes(conn: sqlite3.Connection) -> Tuple[List[int], Dict[int, int]]:
    """
    Load all geo nodes from database
    
    Returns:
        ids: List of geo_ids in ascending order
        id_to_idx: Mapping from geo_id to dense index [0..N-1]
    """
    rows = conn.execute(f"SELECT geo_id FROM {T_PLACES} ORDER BY geo_id ASC;").fetchall()
    ids = [int(r["geo_id"]) for r in rows]
    id_to_idx = {gid: i for i, gid in enumerate(ids)}
    return ids, id_to_idx

