import hashlib
import json
import time


# --- 核心哈希工具 (与编码端保持完全一致) ---

def sha256_hash(input_data):
    """输出32位二进制字符串（补0处理）"""
    sha256 = hashlib.sha256()
    if isinstance(input_data, str):
        input_data = input_data.encode('utf-8')
    sha256.update(input_data)
    hash_bytes = sha256.digest()[:8]
    binary_str = ''.join(f'{byte:08b}' for byte in hash_bytes)
    return binary_str[:32]


# --- 初始映射表生成 (与编码端保持完全一致) ---

def generate_initial_map(key):
    base_groups = ['00', '01', '10', '11']
    at_bases = ['A', 'T']
    gc_bases = ['C', 'G']
    all_bases = at_bases + gc_bases

    while True:
        hash_bin = sha256_hash(key)
        candidate_bases = []
        for i in range(0, len(hash_bin) - 1, 2):
            base_idx = int(hash_bin[i:i + 2], 2) % 4
            base = all_bases[base_idx]
            if base not in candidate_bases and len(candidate_bases) < 4:
                candidate_bases.append(base)

        if len(candidate_bases) < 4:
            key += '#'
            continue

        init_map = {}
        for i, group in enumerate(base_groups):
            if i < len(candidate_bases):
                init_map[group] = candidate_bases[i]

        used_bases = list(init_map.values())
        for group in base_groups:
            if group not in init_map:
                for base in all_bases:
                    if base not in used_bases:
                        init_map[group] = base
                        used_bases.append(base)
                        break

        gc_count = sum(1 for base in init_map.values() if base in gc_bases)
        gc_ratio = (gc_count / 4) * 100
        if 40 <= gc_ratio <= 60:
            return init_map


# --- 动态映射更新 (核心逻辑，必须与编码端逐字一致) ---


# ==========================================
# 1. 映射表更新函数 (移除由未来数据触发的逻辑)
# ==========================================
def update_map(key, processed_bits_count, last_three_bases, current_gc_ratio):
    """
    基于 SHA-256 哈希流生成映射表。
    【创新点改进】：加入 Context-Aware 逻辑，主动降低生成同聚物的概率。
    """
    input_groups = ['00', '01', '10', '11']
    base_lookup = ['A', 'C', 'G', 'T']
    new_map = {}
    assigned_bases = set()
    groups_to_process = list(input_groups)

    # --- 1. 获取“危险碱基” (上一轮的最后一个碱基) ---
    # 如果解码器知道 last_three_bases，它就能推算出谁是危险碱基，从而复现这个逻辑
    danger_base = None
    if last_three_bases:
        danger_base = last_three_bases[-1]

    # --- 2. 设定优先级池 (GC 平衡 + 同聚物规避) ---
    at_bases = ['A', 'T']
    gc_bases = ['C', 'G']
    primary_pool = []
    reserve_pool = []

    # A. 先根据 GC 决定大方向
    if current_gc_ratio > 60:
        raw_primary = at_bases;
        raw_reserve = gc_bases
    elif current_gc_ratio < 40:
        raw_primary = gc_bases;
        raw_reserve = at_bases
    else:
        raw_primary = at_bases + gc_bases;
        raw_reserve = []

    # B. 【关键创新】：从首选池中剔除“危险碱基”
    # 我们希望 map[bit_group] = danger_base 的情况尽可能少发生。
    # 所以把 danger_base 强制扔到 reserve_pool (备选池) 或者放到最后考虑。

    final_primary = [b for b in raw_primary if b != danger_base]
    final_reserve = [b for b in raw_reserve if b != danger_base]

    # 如果 danger_base 本来就在 primary 里，把它移到 reserve 的最末尾
    if danger_base in raw_primary:
        final_reserve.append(danger_base)
    elif danger_base in raw_reserve:
        final_reserve.append(danger_base)  # 保持在 reserve

    # 如果 primary 空了（极端情况），稍微回填一下，但尽量不填 danger_base
    if not final_primary and not final_reserve:
        # 这种情况理论上不会发生，除非 danger_base 是唯一剩下的
        final_primary = [b for b in base_lookup if b != danger_base]
        final_reserve = [danger_base]

    # 现在的 primary_pool 里全是“安全碱基”，reserve_pool 里才包含“危险碱基”
    primary_pool = final_primary
    reserve_pool = final_reserve

    # --- 3. 生成哈希流 (保持不变) ---
    seed_data = f"{key}_{processed_bits_count}_{''.join(last_three_bases)}"
    hash_hex = hashlib.sha256(seed_data.encode()).hexdigest()
    hash_bin_stream = bin(int(hash_hex, 16))[2:].zfill(256)

    # --- 4. 循环匹配 (保持不变，但因为 pool 变了，映射结果会偏向安全碱基) ---
    stream_idx = 0
    num_hash_groups = len(groups_to_process) - 1

    for i in range(num_hash_groups):
        target_group = groups_to_process[i]
        found_valid_base = False

        while not found_valid_base:
            if stream_idx + 2 > len(hash_bin_stream): stream_idx = 0
            bits = hash_bin_stream[stream_idx: stream_idx + 2]
            stream_idx += 2
            base_idx = int(bits, 2)
            candidate = base_lookup[base_idx]

            if candidate in assigned_bases: continue

            # 这里的逻辑会优先从 primary_pool 选
            # 因为 danger_base 被我们人为移到了 reserve_pool
            # 所以只要 primary_pool 还有货，danger_base 就不会被选中！
            available_primary = [b for b in primary_pool if b not in assigned_bases]
            if len(available_primary) > 0 and candidate in reserve_pool: continue

            new_map[target_group] = candidate
            assigned_bases.add(candidate)
            found_valid_base = True

    # --- 5. 填补最后一个 ---
    last_group = groups_to_process[-1]
    all_bases_set = set(['A', 'T', 'C', 'G'])
    remaining_base = list(all_bases_set - assigned_bases)[0]
    new_map[last_group] = remaining_base

    return new_map

def generate_initial_map(key):
    # 简单的初始映射生成，也可以复用 update_map
    return update_map(key, 0, ['A', 'C', 'G'], 50)


# ==========================================
# 3. 解码器 (增加跳过阻断符逻辑)
# ==========================================
def dna_decoding(dna_sequence, key):
    # 假设 generate_initial_map(key) 和 update_map(...) 可用

    current_map = generate_initial_map(key)
    reverse_map = {v: k for k, v in current_map.items()}

    decode_map_history = []
    # 初始状态记录
    decode_map_history.append({"start_base": 0, "end_base": None, "map": current_map})

    binary_sequence = []
    # 历史状态必须严格同步
    last_three = []
    gc_count = 0
    total_bases = 0  # 已经处理的 DNA 碱基总数
    processed_bits = 0  # 已经解码的比特总数

    current_run_length = 0
    repeating_base = None
    MAX_RUN_LIMIT = 6

    # 标记：下一个碱基是否是阻断符 (用于跳过)
    skip_next_base = False

    for base in dna_sequence:

        # 1. --- 映射表更新检查 (B) ---
        # 必须在处理当前碱基之前，基于处理前（total_bases）的状态进行检查
        need_update = False

        if current_run_length > 5:
            need_update = True

        if total_bases > 0 and total_bases % 100 == 0:
            current_gc = (gc_count / total_bases) * 100
            if current_gc < 40 or current_gc > 60:
                need_update = True

        if need_update:
            decode_map_history[-1]["end_base"] = total_bases - 1
            current_gc_ratio = (gc_count / total_bases) * 100

            # 使用当前的历史状态和 processed_bits 来重建映射表
            current_map = update_map(key, processed_bits, last_three, current_gc_ratio)
            reverse_map = {v: k for k, v in current_map.items()}

            decode_map_history.append({
                "start_base": total_bases,
                "end_base": None,
                "map": current_map
            })

        # 2. --- 阻断符处理逻辑 (A) ---
        if skip_next_base:
            # 这是一个由编码器插入的阻断符。只更新历史状态，不解码。

            # 更新历史状态 (total_bases, gc_count, last_three)
            if base in ['C', 'G']: gc_count += 1
            total_bases += 1
            last_three.append(base)
            if len(last_three) > 6: last_three.pop(0)

            # 更新 RLL 状态 (阻断符打破了 run)
            current_run_length = 1
            repeating_base = base

            # 重置标记并继续处理下一个碱基
            skip_next_base = False
            continue

        # 3. --- 正常解码 (C) ---
        bit_group = reverse_map.get(base)
        if bit_group is None:
            raise ValueError(f"解码错误：碱基 {base} 不在当前映射表中 (Pos: {total_bases})")

        binary_sequence.append(bit_group)
        processed_bits += 2  # 只有数据碱基才增加 processed_bits

        # 4. --- 更新 RLL 和历史状态 (D) ---

        # a. RLL 计数
        if base == repeating_base:
            current_run_length += 1
        else:
            current_run_length = 1
            repeating_base = base

        # b. 预测阻断符 (如果 RLL 达到极限，设置标记，下一个碱基必然是阻断符)
        if current_run_length >= MAX_RUN_LIMIT:
            skip_next_base = True

        # c. 更新历史状态
        if base in ['C', 'G']: gc_count += 1
        total_bases += 1
        last_three.append(base)
        if len(last_three) > 6: last_three.pop(0)

    # 循环结束后的收尾工作
    if decode_map_history:
        decode_map_history[-1]["end_base"] = total_bases - 1


    return ''.join(binary_sequence)


def binary_str_to_bytes(binary_str):
    """将二进制字符串转换回字节流"""
    # 确保长度是 8 的倍数
    if len(binary_str) % 8 != 0:
        # 通常编码器会补齐，这里作为保险
        padding = 8 - (len(binary_str) % 8)
        binary_str += '0' * padding

    bytes_data = bytearray()
    for i in range(0, len(binary_str), 8):
        byte = binary_str[i:i + 8]
        bytes_data.append(int(byte, 2))
    return bytes(bytes_data)

