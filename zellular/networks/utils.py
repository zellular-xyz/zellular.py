from eigensdk.crypto.bls import attestation


def parse_g2_key(op: dict):
    if "public_key_g2" in op:
        public_key_g2_str = op["public_key_g2"]
    else:    
        public_key_g2_str = f"1 {op['pubkeyG2_X'][1]} {op['pubkeyG2_X'][0]} {op['pubkeyG2_Y'][1]} {op['pubkeyG2_Y'][0]}"
    g2 = attestation.new_zero_g2_point()
    g2.setStr(public_key_g2_str.encode("utf-8"))
    return g2


def aggregate_g2_keys(operators: list) -> attestation.G2Point:
    aggregated = attestation.new_zero_g2_point()
    for op in operators:
        aggregated += op.public_key_g2
    return aggregated
