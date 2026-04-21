import hashlib
import random
import json  # 用于序列化映射表


# --- 核心哈希工具 ---

def sha256_hash(input_data):
    """与编码端完全一致的哈希函数：输出32位二进制字符串（补0处理）"""
    sha256 = hashlib.sha256()
    if isinstance(input_data, str):
        input_data = input_data.encode('utf-8')
    sha256.update(input_data)

    # 取前8字节哈希（64比特），截断为32位
    hash_bytes = sha256.digest()[:8]
    binary_str = ''.join(f'{byte:08b}' for byte in hash_bytes)
    return binary_str[:32]


# --- 映射表生成逻辑 ---

def generate_initial_map(key):
    """初始映射表生成函数"""
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

        # 校验GC占比
        gc_count = sum(1 for base in init_map.values() if base in gc_bases)
        gc_ratio = (gc_count / 4) * 100
        if 40 <= gc_ratio <= 60:
            return init_map


# ==========================================
# 1. 映射表更新函数 (移除由未来数据触发的逻辑)
# ==========================================
def update_map(key, processed_bits_count, last_three_bases, current_gc_ratio):
    """
    加入 Context-Aware 逻辑，主动降低生成同聚物的概率。
    """
    input_groups = ['00', '01', '10', '11']
    base_lookup = ['A', 'C', 'G', 'T']
    new_map = {}
    assigned_bases = set()
    groups_to_process = list(input_groups)
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

    # B：从首选池中剔除“危险碱基”
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

    # --- 3. 生成哈希流---
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
    # 简单的初始映射生成
    return update_map(key, 0, ['A', 'C', 'G'], 50)


# ==========================================
# 2. 编码器 (增加同聚物阻断逻辑)
# ==========================================
def dna_encoding(binary_sequence, key):
    current_map = generate_initial_map(key)
    map_history = []
    map_history.append({"start_base": 0, "end_base": None, "map": current_map})

    dna_sequence = []
    last_three = []  # 保持简单的历史记录
    gc_count = 0
    total_bases = 0
    processed_bits = 0

    current_run_length = 0
    repeating_base = None

    MAX_RUN_LIMIT = 6  # 设定阈值：连续 5 个相同就插入阻断符

    i = 0
    while i < len(binary_sequence):
        bit_group = binary_sequence[i:i + 2]
        # 1. 检查是否需要更新映射表
        need_update = False
        if total_bases > 0 and total_bases % 100 == 0:
            current_gc = (gc_count / total_bases) * 100
            if current_gc < 40 or current_gc > 60:
                need_update = True

        if current_run_length > 5:
            need_update = True


        if need_update:
            map_history[-1]["end_base"] = total_bases - 1
            current_gc_ratio = (gc_count / total_bases) * 100

            # 不再传递 prev_bit_group 或 trigger，只基于历史
            current_map = update_map(key, processed_bits, last_three, current_gc_ratio)

            map_history.append({
                "start_base": total_bases,
                "end_base": None,
                "map": current_map
            })

        if current_run_length >= MAX_RUN_LIMIT:
            # 1. 选择阻断碱基 (Breaker)
            # 简单的策略：选择当前重复碱基的互补碱基，或者查表找一个不一样的
            breaker_base = 'C' if repeating_base == 'A' else 'A'
            

            # 2. 插入 DNA 序列 (这个碱基不消耗二进制数据!)
            dna_sequence.append(breaker_base)

            # 3. 更新状态 (因为插入了新碱基，Run Length 被打破)
            current_run_length = 1
            repeating_base = breaker_base

            # 4. 更新统计信息
            if breaker_base in ['C', 'G']: gc_count += 1
            total_bases += 1
            last_three.append(breaker_base)
            if len(last_three) > 6: last_three.pop(0)

            # 5. 重要：continue！
            # 我们只插入了物理标记，还没有处理当前的 bit_group (i 没有增加)
            # 下一轮循环会用当前的 map 和 bits 再次尝试编码，
            # 但因为有了阻断符，这次生成的碱基即使和之前一样，也不会连成更长的同聚物了。
            continue

        # 2. 编码
        candidate_base = current_map[bit_group]
        dna_sequence.append(candidate_base)

        # 3. 更新 Run Length
        if candidate_base == repeating_base:
            current_run_length += 1
        else:
            current_run_length = 1
            repeating_base = candidate_base

        # 4. 更新其他状态
        if candidate_base in ['C', 'G']: gc_count += 1
        total_bases += 1
        last_three.append(candidate_base)
        if len(last_three) > 6: last_three.pop(0)

        processed_bits += 2
        i += 2  # 推进比特索引

    if map_history:
        map_history[-1]["end_base"] = total_bases - 1

    return ''.join(dna_sequence)




def bytes_to_binary_str(byte_data):
    """将字节流转换为二进制字符串（确保每个字节8位，高位补0）"""
    return ''.join(f'{byte:08b}' for byte in byte_data)


if __name__ == "__main__":
    import time

    # 假设你有一个名为 DNA_validator.py 的文件用于验证
    # 如果没有，请注释掉验证部分
    try:
        from DNA_validator import validate_dna_sequence, print_validation_report

        has_validator = True
    except ImportError:
        has_validator = False
        print("Warning: DNA_validator module not found. Skipping validation.")

    dna_save_path = "image_dna_sequence.txt"


    image_path = "1.png"
    key = "b5b6e940db20c00b0000000000000000"

    with open(image_path, "rb") as f:
        image_data = f.read()

    binary_str = bytes_to_binary_str(image_data)

    print(f"数据大小：{len(image_data)} 字节 → 预计DNA长度：{len(image_data) * 4} bp")

    begin = time.time()
    dna = dna_encoding(binary_str, key)
    end = time.time()

    print(f"编码耗时：{(end - begin):.4f}s")

    if has_validator:
        result = validate_dna_sequence(dna)
        print_validation_report(result)

    with open(dna_save_path, "w", encoding="utf-8") as f:
        f.write(dna)
    print(f"\nDNA碱基序列已保存至：{dna_save_path}")
