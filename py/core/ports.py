"""
Front-panel port helpers using BF-RT.
Execute inside bfshell -b so that `bfrt` is available; pass in program pipe handle.
"""
import sys
from typing import Dict, Tuple
from loguru import logger

logger.remove()
logger.add(sys.stdout, level="INFO")

# Types
PortCfg = Tuple[int, int]  # (CONN_ID, CHNL_ID)

def add_port(bfrt, conn_id: int, chnl_id: int, speed: str = 'BF_SPEED_100G',
             fec: str = 'BF_FEC_TYP_NONE', an: str = 'PM_AN_FORCE_DISABLE') -> None:
    dp = bfrt.port.port_hdl_info.get(CONN_ID=conn_id, CHNL_ID=chnl_id, print_ents=False).data[b'$DEV_PORT']
    bfrt.port.port.add(DEV_PORT=dp, SPEED=speed, FEC=fec, AUTO_NEGOTIATION=an, PORT_ENABLE=True)

def add_ports_from_map(bfrt, port_map: Dict[str, PortCfg]) -> None:
    logger.info("Enabling ports from provided port map...") 
    for name, (conn, ch) in port_map.items():
        logger.info(f"Enabling port {name}: CONN_ID={conn}/CHNL_ID={ch}")
        add_port(bfrt, conn, ch)
