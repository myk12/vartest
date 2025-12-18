/* ===============================================================
 *         Spine-Leaf Topology P4 Program for Tofino Switch
 * ===============================================================
 * This P4 program implements a basic spine-leaf switching logic
 * for a Tofino switch in a spine-leaf topology.
 * The program classifies packets based on their ingress port
 * to determine whether they are from leaf switches or spine switches,
 * and forwards them accordingly.
 * =============================================================== */

#include <core.p4>
#if __TARGET_TOFINO__ == 2
#include <t2na.p4>
#else
#include <tna.p4>
#endif

#include "include/headers.p4"
#include "include/util.p4"

//--------------------------------------------
// Constants and Type Definitions
//--------------------------------------------
#define ETHERTYPE_IPV4 0x0800

struct header_t {
    ethernet_h ethernet;
    ipv4_h     ipv4;
}

// define custom metadata to hold logical role
struct metadata_t {
    // core logical role of the switch
    // 1-4 = leaf 1-4, 10 = spine elec, 20 = spine optical
    bit<8> logical_switch_id;
}

// --------------------------------------------
// Ingress Parser
// --------------------------------------------
parser SnosParser(
    packet_in packet,
    out header_t hdr,
    out metadata_t ig_md,
    out ingress_intrinsic_metadata_t ig_intr_md
) {
    TofinoIngressParser() tofino_parser;

    state start {
        tofino_parser.apply(packet, ig_intr_md);
        transition parse_ethernet;
    }

    state parse_ethernet {
        packet.extract(hdr.ethernet);
        transition select(hdr.ethernet.ether_type) {
            ETHERTYPE_IPV4: parse_ipv4;
            default: accept;
        }
    }

    state parse_ipv4 {
        packet.extract(hdr.ipv4);
        transition accept;
    }
}

// -------------------------------------------
// Ingress Control: Core Spine-Leaf Logic
// -------------------------------------------
control SnosIngress(
    inout header_t hdr,
    inout metadata_t ig_md,
    in ingress_intrinsic_metadata_t ig_intr_md,
    in ingress_intrinsic_metadata_from_parser_t ig_intr_prsr_md,
    inout ingress_intrinsic_metadata_for_deparser_t ig_intr_dprsr_md,
    inout ingress_intrinsic_metadata_for_tm_t ig_intr_tm_md) {

    // Define Actions
    action drop() {
        ig_intr_dprsr_md.drop_ctl = 0x1;
    }

    action set_logical_switch(bit<8> switch_id) {
        ig_md.logical_switch_id = switch_id;
    }

    // standard L3 forwarding action
    // param: destination MAC address and egress port
    action ipv4_forward(bit<48> next_hop_dmac, PortId_t port) {
        // 1. update src MAC
        hdr.ethernet.src_addr = hdr.ethernet.dst_addr;

        // 2. update dst MAC
        hdr.ethernet.dst_addr = next_hop_dmac;

        // 3. decrement TTL
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;

        // 4. set egress port
        ig_intr_tm_md.ucast_egress_port = port;
    }

    // Table Definitions

    // [Table 1] virtualize mapping of physical port to logical role
    // function: map physical port to logical switch id
    table t_port_mapping {
        key = {
            ig_intr_md.ingress_port: exact;
        }
        actions = {
            set_logical_switch;
            drop;
        }
        size = 256;
        const default_action = drop();
    }

    // [Table 2] unified forwarding table for spine and leaf switches
    // function: lookup this table no matter leaf or spine
    // key: logical_switch_id is included in the key to separate entries for different logical switches
    table t_ipv4_lpm {
        key = {
            ig_md.logical_switch_id: exact;
            hdr.ipv4.dst_addr: lpm;
        }
        actions = {
            ipv4_forward;
            drop;
        }
        size = 4096;
        const default_action = drop();
    }

    // Apply Logic
    apply {
        // First, map physical port to logical switch id
        if (hdr.ipv4.isValid()) {
            t_port_mapping.apply();

            // Then, perform unified forwarding lookup
            t_ipv4_lpm.apply();
        } else {
            // Non-IPv4 packets are dropped
            drop();
        }
    }
}

// -------------------------------------------
// Ingress Deparser - keep it simple
// -------------------------------------------
control SnosIngressDeparser(
    packet_out packet,
    inout header_t hdr,
    in metadata_t ig_md,
    in ingress_intrinsic_metadata_for_deparser_t ig_intr_dprsr_md
) {

    apply {

        // Emit headers
        packet.emit(hdr.ethernet);
        packet.emit(hdr.ipv4);
    }
}

// -------------------------------------------
// Egress Parser - keep it simple
// -------------------------------------------
control SnosEgress(
    inout header_t hdr,
    inout metadata_t eg_md,
    in egress_intrinsic_metadata_t eg_intr_md,
    in egress_intrinsic_metadata_from_parser_t eg_intr_dprsr_md,
    inout egress_intrinsic_metadata_for_deparser_t eg_intr_md_for_dprsr,
    inout egress_intrinsic_metadata_for_output_port_t eg_intr_md_for_oport
) {
    apply {
        // No egress parsing for now
    }
}

// -------------------------------------------
// Egress Parser & Deparser
// -------------------------------------------
parser SnosEgressParser(
    packet_in packet,
    out header_t hdr,
    out metadata_t eg_md,
    out egress_intrinsic_metadata_t eg_intr_md
) {
    TofinoEgressParser() tofino_parser;

    state start {
        tofino_parser.apply(packet, eg_intr_md);
        transition accept;
    }
}

control SnosEgressDeparser(
    packet_out packet,
    inout header_t hdr,
    in metadata_t eg_md,
    in egress_intrinsic_metadata_for_deparser_t eg_intr_dprsr_md
) {
    apply {
        packet.emit(hdr.ethernet);
        packet.emit(hdr.ipv4);
    }
}

// -------------------------------------------
// Main Pipeline and Switch Declaration
// -------------------------------------------
Pipeline(SnosParser(),
    SnosIngress(),
    SnosIngressDeparser(),
    SnosEgressParser(),
    SnosEgress(),
    SnosEgressDeparser()) pipe;

Switch(pipe) main;
