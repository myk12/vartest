"""
Forward table programming for ts_pipeline.p4
"""
import sys
from typing import Any
from loguru import logger

logger.remove()
logger.add(sys.stdout, level="INFO")

def program_forward_table(pipe: Any, exp_id: int, egress_dev_port: int, qid: int = 0) -> None:
    forward = pipe.Ingress.forward
    logger.info(f"Adding forward: exp_id={exp_id} -> DEV_PORT={egress_dev_port}, qid={qid}")
    forward.add_with_set_port_qid(exp_id=exp_id, egress_port=egress_dev_port, qid=qid)

def delete_forward_entry(pipe: Any, exp_id: int) -> None:
    forward = pipe.Ingress.forward
    try:
        forward.delete(key={'exp_id': exp_id})
        print(f"Deleted forward entry for exp_id={exp_id}")
    except Exception as e:
        print(f"Delete forward failed for exp_id={exp_id}: {e}")

def program_pass_through(pipe: Any, ingress_dev_port: int, egress_dev_port: int) -> None:
    logger.info(f"Adding pass-through: ingress DEV_PORT={ingress_dev_port} -> egress DEV_PORT={egress_dev_port}")
    t = pipe.Ingress.pass_through
    logger.info(f"Pass-through: ingress DEV_PORT={ingress_dev_port} -> egress DEV_PORT={egress_dev_port}")
    t.add_with_set_port(ingress_port=ingress_dev_port, egress_port=egress_dev_port)
