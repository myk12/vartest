import socket
from scapy.all import *

hostname = socket.gethostname()
print(hostname)

bfrt_pipe = bfrt.dptp_tx.pipe

DPTP_PUSH_CLOCK = 0
DPTP_INIT = 1
DPTP_REQ = 2
DPTP_RESP = 3

def clear_all(pipe, verbose=True, batching=True):
    global bfrt
    
    # The order is important. We do want to clear from the top, i.e.
    # delete objects that use other objects, e.g. table entries use
    # selector groups and selector groups use action profile members

    for table_types in (['MATCH_DIRECT', 'MATCH_INDIRECT_SELECTOR'],
                        ['REGISTER'],
                        ['SELECTOR'],
                        ['ACTION_PROFILE']):
        for table in pipe.info(return_info=True, print_info=False):
            if table['type'] in table_types:
                if verbose:
                    print("Clearing table {:<40} ... ".
                          format(table['full_name']), end='', flush=True)
                table['node'].clear(batch=batching)
                if verbose:
                    print('Done')

clear_all(bfrt_pipe, verbose=False) 

#############################################
# Configure front-panel ports
#############################################
master_sw = "switch7-neptune"
master_sw = "switch6-uranus"
master_sw = "switch4-jupiter"
master_host = 0
master_port = 28
master_port = 29
master_port = 31
master_port = 27
master_port = 32
master_port = 25
master_port = 17
master_port = 24
master_port = 16
master_port = 8
master_port = 31
#master_host = 29

client_sw = "switch6-uranus"
client_sw = "switch7-neptune"
client_sw = "switch4-jupiter"
client_host = 0
client_port = 30
client_port = 29
client_port = 28
client_port = 27
client_port = 8
client_port = 31
client_port = 26
client_port = 18
client_port = 24
client_port = 16
client_port = 32
#client_host = 30


port_map = {
    4   :   160,
    8   :   192,
    16  :   264,
    17  :   400,
    18  :   392,
    19  :   416,
    20  :   408,
    21  :   432,
    22  :   424,
    23  :   448,
    24  :   440,
    25  :   56,
    26  :   64,
    27  :   40,
    28  :   48,
    29  :   24,
    30  :   32,
    31  :   8,
    32  :   16
    }

fp_port_configs = []
configs = [ 
    ('4/0', '100G', 'NONE', 2),
    ('8/0', '100G', 'NONE', 2),
    ('12/0', '100G', 'NONE', 2),
    ('16/0', '100G', 'NONE', 2),
    ('17/0', '100G', 'NONE', 2),
    ('18/0', '100G', 'NONE', 2),
    ('19/0', '100G', 'NONE', 2),
    ('20/0', '100G', 'NONE', 2),
    ('22/0', '100G', 'NONE', 2),
    ('24/0', '100G', 'NONE', 2),
    ('25/0', '100G', 'NONE', 2),
    ('26/0', '100G', 'NONE', 2),
    ('27/0', '100G', 'NONE', 2),
    ('28/0', '100G', 'NONE', 2),
    ('29/0', '100G', 'NONE', 2),
    ('30/0', '100G', 'NONE', 2),
    ('31/0', '100G', 'NONE', 2),
    ('32/0', '100G', 'NONE', 2),
]

for config in configs:
    port = int(config[0][:-2])
    #print(f"port is {port}")
    if hostname == master_sw and (port == master_port or port == master_host) or \
        hostname == client_sw and (port == client_port or port == client_host):
        fp_port_configs.append(config)

'''
fp_port_configs = [ 
                    ('4/0', '100G', 'NONE', 2),
                    ('8/0', '100G', 'NONE', 2),
                    ('12/0', '100G', 'NONE', 2),
                    ('16/0', '100G', 'NONE', 2),
                    ('20/0', '100G', 'NONE', 2),
                    ('22/0', '100G', 'NONE', 2),
                    ('24/0', '100G', 'NONE', 2),
                    ('25/0', '100G', 'NONE', 2),
                    ('28/0', '100G', 'NONE', 2),
                    ('30/0', '100G', 'NONE', 2),
                    ('31/0', '100G', 'NONE', 2),
                    ('32/0', '100G', 'NONE', 2),
                ]
'''

def add_port_config(port_config):
    speed_dict = {'10G':'BF_SPEED_10G', '25G':'BF_SPEED_25G', '40G':'BF_SPEED_40G', '50G':'BF_SPEED_50G', '100G':'BF_SPEED_100G'}
    fec_dict = {'NONE':'BF_FEC_TYP_NONE', 'FC':'BF_FEC_TYP_FC', 'RS':'BF_FEC_TYP_RS'}
    an_dict = {0:'PM_AN_DEFAULT', 1:'PM_AN_FORCE_ENABLE', 2:'PM_AN_FORCE_DISABLE'}
    lanes_dict = {'10G':(0,1,2,3), '25G':(0,1,2,3), '40G':(0,), '50G':(0,2), '100G':(0,)}
    
    # extract and map values from the config first
    conf_port = int(port_config[0].split('/')[0])
    lane = port_config[0].split('/')[1]
    conf_speed = speed_dict[port_config[1]]
    conf_fec = fec_dict[port_config[2]]
    conf_an = an_dict[port_config[3]]


    if lane == '-': # need to add all possible lanes
        lanes = lanes_dict[port_config[1]]
        for lane in lanes:
            dp = bfrt.port.port_hdl_info.get(CONN_ID=conf_port, CHNL_ID=lane, print_ents=False).data[b'$DEV_PORT']
            bfrt.port.port.add(DEV_PORT=dp, SPEED=conf_speed, FEC=conf_fec, AUTO_NEGOTIATION=conf_an, PORT_ENABLE=True)
    else: # specific lane is requested
        conf_lane = int(lane)
        dp = bfrt.port.port_hdl_info.get(CONN_ID=conf_port, CHNL_ID=conf_lane, print_ents=False).data[b'$DEV_PORT']
        bfrt.port.port.add(DEV_PORT=dp, SPEED=conf_speed, FEC=conf_fec, AUTO_NEGOTIATION=conf_an, PORT_ENABLE=True)

for config in fp_port_configs:
    add_port_config(config)


forward = bfrt_pipe.Ingress.forward
#forward.set_default_with_set_port(egress_port=424)

if hostname == master_sw:
    forward.add_with_set_port(dptp_type = DPTP_PUSH_CLOCK, egress_port = port_map[master_port])
    forward.add_with_set_port(dptp_type = DPTP_REQ, egress_port = port_map[master_port])
if hostname == client_sw:
    forward.add_with_set_port(dptp_type = DPTP_INIT, egress_port = port_map[client_port])
    #pass

forward_bg = bfrt_pipe.Ingress.forward_bg
#forward_bg.add_with_set_bg_port(app_id = 2, egress_port = port_map[client_port])
#forward_bg.add_with_set_bg_port(app_id = 3, egress_port = port_map[client_port])
forward_bg.add_with_set_bg_port(app_id = 2, egress_port = port_map[master_port])
forward_bg.add_with_set_bg_port(app_id = 3, egress_port = port_map[master_port])

#dev_port = port_map[client_port]
dev_port = port_map[master_port]
queue_id = 0
pipe = dev_port >> 7

entry = bfrt.tf2.tm.port.cfg.get(dev_port, print_ents=False)
pg_id = entry.data[b'pg_id']
pg_queue = entry.data[b'egress_qid_queues'][queue_id]

print('DEV_PORT: {}  QueueID: {}  --> Pipe: {}  PG_ID: {} PG_QUEUE: {}'.format(
    dev_port, queue_id, pipe, pg_id, pg_queue))

bfrt.tf2.tm.queue.sched_cfg.mod(pipe=pipe, pg_id=pg_id, pg_queue=pg_queue, max_priority=1)
