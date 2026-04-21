import hashlib
import time


# --- 核心哈希工具 (必须与编码器一致) ---
def sha256_hash(input_data):
    sha256 = hashlib.sha256()
    if isinstance(input_data, str):
        input_data = input_data.encode('utf-8')
    sha256.update(input_data)
    hash_bytes = sha256.digest()[:8]
    binary_str = ''.join(f'{byte:08b}' for byte in hash_bytes)
    return binary_str[:32]


# --- 动态映射更新 (必须与编码器一致) ---
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
    return update_map(key, 0, ['A', 'C', 'G'], 50)


# --- 解码器 ---
def dna_decoding(dna_sequence, key):
    current_map = generate_initial_map(key)
    reverse_map = {v: k for k, v in current_map.items()}

    binary_sequence = []
    last_three = []
    gc_count = 0
    total_bases = 0
    processed_bits = 0

    current_run_length = 0
    repeating_base = None
    MAX_RUN_LIMIT = 4

    skip_next_base = False

    for base in dna_sequence:

        # ==========================================
        # 核心修复：阻断符处理逻辑
        # ==========================================
        if skip_next_base:
            # 致命漏洞修复：将换表逻辑移入此处！
            # 这样保证了：解码器遇到阻断符时，是基于与编码器完全相同的 run_length 状态进行换表的。
            need_update = False
            if total_bases > 0 and total_bases % 100 == 0:
                current_gc = (gc_count / total_bases) * 100
                if current_gc < 40 or current_gc > 60:
                    need_update = True
            if current_run_length > 3:
                need_update = True

            if need_update:
                current_gc_ratio = (gc_count / total_bases) * 100 if total_bases > 0 else 50
                current_map = update_map(key, processed_bits, last_three, current_gc_ratio)
                reverse_map = {v: k for k, v in current_map.items()}
            # ------------------------------------------

            # 处理阻断符本身：只更新物理状态，不解码数据
            if base in ['C', 'G']: gc_count += 1
            total_bases += 1
            last_three.append(base)
            if len(last_three) > 6: last_three.pop(0)

            current_run_length = 1
            repeating_base = base
            skip_next_base = False
            continue

        # 正常解码流程前的常规 GC 检查
        need_update = False
        if total_bases > 0 and total_bases % 100 == 0:
            current_gc = (gc_count / total_bases) * 100
            if current_gc < 40 or current_gc > 60:
                need_update = True

        if need_update:
            current_gc_ratio = (gc_count / total_bases) * 100 if total_bases > 0 else 50
            current_map = update_map(key, processed_bits, last_three, current_gc_ratio)
            reverse_map = {v: k for k, v in current_map.items()}

        # 正常解码
        bit_group = reverse_map.get(base)
        if bit_group is None:
            raise ValueError(f"解码错误：碱基 {base} 不在当前映射表中")

        binary_sequence.append(bit_group)
        processed_bits += 2

        if base == repeating_base:
            current_run_length += 1
        else:
            current_run_length = 1
            repeating_base = base

        if current_run_length >= MAX_RUN_LIMIT:
            skip_next_base = True

        if base in ['C', 'G']: gc_count += 1
        total_bases += 1
        last_three.append(base)
        if len(last_three) > 6: last_three.pop(0)

    return ''.join(binary_sequence)


def binary_str_to_bytes(binary_str):
    if len(binary_str) % 8 != 0:
        padding = 8 - (len(binary_str) % 8)
        binary_str += '0' * padding
    bytes_data = bytearray()
    for i in range(0, len(binary_str), 8):
        bytes_data.append(int(binary_str[i:i + 8], 2))
    return bytes(bytes_data)

