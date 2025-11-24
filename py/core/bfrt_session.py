"""
BF-RT session helper.
This module is intended to be executed inside bfshell -b (where `bfrt` is available)
or via the BF-RT Python client, depending on your SDE. For portability, we detect
whether a global `bfrt` symbol exists.
"""
from typing import Any
import os

def get_bfrt_handle() -> Any:
    """Return the global `bfrt` handle if available, else raise RuntimeError.
    In bfshell -b, a global `bfrt` is injected; in standalone client you may
    need to initialize a connection differently.
    """
    glb = globals()
    if 'bfrt' not in glb:
        raise RuntimeError(
            "bfrt is not available in globals(). Run this script via bfshell -b or "
            "adapt bfrt client initialization for your SDE.")
    return glb['bfrt']

def clear_all(pipe, verbose: bool = True, batching: bool = True) -> None:
    """Clear tables and state in a safe top-down order."""
    for table_types in (['MATCH_DIRECT', 'MATCH_INDIRECT_SELECTOR'],
                        ['REGISTER'],
                        ['SELECTOR'],
                        ['ACTION_PROFILE']):
        for table in pipe.info(return_info=True, print_info=False):
            if table['type'] in table_types:
                if verbose:
                    print(f"Clearing table {table['full_name']:<40} ... ", end='', flush=True)
                table['node'].clear(batch=batching)
                if verbose:
                    print('Done')
