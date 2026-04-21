import hashlib
import json


# --- 核心哈希工具 ---
def sha256_hash(input_data):
    sha256 = hashlib.sha256()
    if isinstance(input_data, str):
        input_data = input_data.encode('utf-8')
    sha256.update(input_data)
    hash_bytes = sha256.digest()[:8]
    binary_str = ''.join(f'{byte:08b}' for byte in hash_bytes)
    return binary_str[:32]


# --- 动态映射更新 (核心算法) ---
def update_map(key, processed_bits_count, last_three_bases, current_gc_ratio):
    input_groups = ['00', '01', '10', '11']
    base_lookup = ['A', 'C', 'G', 'T']
    new_map = {}
    assigned_bases = set()
    groups_to_process = list(input_groups)

    danger_base = last_three_bases[-1] if last_three_bases else None

    at_bases, gc_bases = ['A', 'T'], ['C', 'G']
    if current_gc_ratio > 60:
        raw_primary, raw_reserve = at_bases, gc_bases
    elif current_gc_ratio < 40:
        raw_primary, raw_reserve = gc_bases, at_bases
    else:
        raw_primary, raw_reserve = at_bases + gc_bases, []

    final_primary = [b for b in raw_primary if b != danger_base]
    final_reserve = [b for b in raw_reserve if b != danger_base]
    if danger_base in raw_primary:
        final_reserve.append(danger_base)
    elif danger_base in raw_reserve:
        final_reserve.append(danger_base)

    if not final_primary and not final_reserve:
        final_primary = [b for b in base_lookup if b != danger_base]
        final_reserve = [danger_base]

    seed_data = f"{key}_{processed_bits_count}_{''.join(last_three_bases)}"
    hash_hex = hashlib.sha256(seed_data.encode()).hexdigest()
    hash_bin_stream = bin(int(hash_hex, 16))[2:].zfill(256)

    stream_idx = 0
    for i in range(3):
        while True:
            if stream_idx + 2 > len(hash_bin_stream): stream_idx = 0
            bits = hash_bin_stream[stream_idx: stream_idx + 2]
            stream_idx += 2
            candidate = base_lookup[int(bits, 2)]
            if candidate in assigned_bases: continue
            if len([b for b in final_primary if b not in assigned_bases]) > 0 and candidate in final_reserve: continue
            new_map[input_groups[i]] = candidate
            assigned_bases.add(candidate)
            break

    new_map[input_groups[-1]] = list(set(['A', 'T', 'C', 'G']) - assigned_bases)[0]
    return new_map


def generate_initial_map(key):
    # 统一使用 update_map 初始化，确保编解码绝对一致
    return update_map(key, 0, ['A', 'C', 'G'], 50)


# --- 编码器 ---
def dna_encoding(binary_sequence, key):
    current_map = generate_initial_map(key)
    dna_sequence = []
    last_three = []
    gc_count = 0
    total_bases = 0
    processed_bits = 0
    current_run_length = 0
    repeating_base = None

    MAX_RUN_LIMIT = 4  # 阈值设为4：达到4个时阻断，保证序列中最长为3

    i = 0
    while i < len(binary_sequence):
        bit_group = binary_sequence[i:i + 2]

        # 1. 检查是否需要更新映射表 (软约束预警)
        need_update = False
        if total_bases > 0 and total_bases % 100 == 0:
            current_gc = (gc_count / total_bases) * 100
            if current_gc < 40 or current_gc > 60:
                need_update = True

        # 当 run_length 达到 3 时，预警并在下一轮强制换表
        if current_run_length > 3:
            need_update = True

        if need_update:
            current_gc_ratio = (gc_count / total_bases) * 100 if total_bases > 0 else 50
            current_map = update_map(key, processed_bits, last_three, current_gc_ratio)

        # 2. 硬约束阻断逻辑
        if current_run_length >= MAX_RUN_LIMIT:
            breaker_base = 'C' if repeating_base == 'A' else 'A'
            dna_sequence.append(breaker_base)

            current_run_length = 1
            repeating_base = breaker_base
            if breaker_base in ['C', 'G']: gc_count += 1
            total_bases += 1
            last_three.append(breaker_base)
            if len(last_three) > 6: last_three.pop(0)
            continue

        # 3. 正常编码
        candidate_base = current_map[bit_group]
        dna_sequence.append(candidate_base)

        if candidate_base == repeating_base:
            current_run_length += 1
        else:
            current_run_length = 1
            repeating_base = candidate_base

        if candidate_base in ['C', 'G']: gc_count += 1
        total_bases += 1
        last_three.append(candidate_base)
        if len(last_three) > 6: last_three.pop(0)

        processed_bits += 2
        i += 2

    return ''.join(dna_sequence)


def bytes_to_binary_str(byte_data):
    return ''.join(f'{byte:08b}' for byte in byte_data)

