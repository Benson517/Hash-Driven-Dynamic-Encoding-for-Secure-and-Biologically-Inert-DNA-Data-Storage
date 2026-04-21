# stress_test.py
# DNA编码器 + 双约束 极端压力测试（10000次全场景验证）
# 完全适配我们之前的 encoder + validator
import os
import random
import string
from tqdm import tqdm
from DNAcode import dna_encoding
from DNA_validator import validate_dna_sequence, print_validation_report

def bytes_to_binary_str(byte_data):
    """将字节流转换为二进制字符串（每个字节8位，高位补0）"""
    return ''.join(f'{byte:08b}' for byte in byte_data)


def random_bytes(n: int) -> bytes:
    """生成指定字节数的随机数据"""
    return bytes(random.randint(0, 255) for _ in range(n))


def stress_test(rounds: int = 10000, min_size: int = 50, max_size: int = 5000):
    """
    终极压力测试
    - 每次使用全新随机密钥
    - 数据长度在 50~5000 字节间随机
    - 包含极端情况：全0、全1、长重复、超高/超低GC倾向数据
    """
    print(f"开始执行 {rounds:,} 轮极端压力测试……")
    print("每轮：全新密钥 + 随机长度 + 随机内容 → 编码 → 严格校验")
    print("-" * 80)

    failed = 0
    stats = {
        "lengths": [],
        "gc_rates": [],
        "max_homo": []
    }

    # 使用 tqdm 进度条，美观又专业
    for i in tqdm(range(1, rounds + 1), desc="压力测试进度", unit="轮"):
        # 1. 随机密钥（每次都不一样）
        key_bytes = os.urandom(16)  # 等价于 random_bytes(16)
        key = key_bytes.hex()  # 转换为32字符的十六进制字符串（16字节→32 hex字符）


        # 2. 随机生成测试数据（包含极端情况）
        size = random.randint(min_size, max_size)

        # 70% 普通随机，30% 极端偏置数据（模拟最恶劣情况）
        if random.random() < 0.3:
            # 极端数据：全0、全1、超高GC、超低GC、长重复块
            case = random.choice([
                b"\x00" * size,  # 全0 → 容易产生同聚物
                b"\xFF" * size,  # 全1
                b"\xAA" * (size // 2) + b"\x55" * (size // 2),  # 01010101...
                bytes([0b00110110] * size),  # 手动构造高GC（60%+）
                bytes([0b00010010] * size),  # 手动构造低GC（<40%）
            ])
            data = case
        else:
            data = random_bytes(size)

        # 3. 编码
        try:
            binary_str = bytes_to_binary_str(data)
            dna = dna_encoding(binary_str,key)
        except Exception as e:
            print(f"\n编码异常！第 {i} 轮，长度 {len(data)} 字节")
            raise e

        # 4. 严格校验
        result = validate_dna_sequence(dna, gc_range=(40.0, 60.0), max_homopolymer=3)

        # 5. 记录与判断
        stats["lengths"].append(len(dna))
        stats["gc_rates"].append(result["gc_content_%"])
        stats["max_homo"].append(result["max_homopolymer"])

        # 修正压力测试中的密钥打印部分
        if not result["valid"]:
            failed += 1
            print(f"\n发现失败案例！第 {i} 轮")
            print(f"数据长度: {len(data)} 字节 → DNA长度: {len(dna)} bp")
            # 直接截取字符串前8个字符（原错误：key[:8].hex()）
            print(f"密钥前8字符: {key[:8]}")
            print(f"原始数据前50字节: {data[:50].hex()}")  # 限制打印长度，避免刷屏
            print_validation_report(result)
            print("即将中断测试……")
            return False, stats

    # 全程通过！
    success_rate = 100.0
    print("\n" + "=" * 80)
    print("压力测试完成！全量通过！".center(80))
    print("=" * 80)
    print(f"总测试轮数     : {rounds:,} 轮")
    print(f"数据长度范围   : {min_size} ~ {max_size} 字节")
    print(f"DNA序列总长    : {sum(stats['lengths']):,} bp")
    print(f"平均 GC 含量   : {sum(stats['gc_rates']) / len(stats['gc_rates']):.3f}%")
    print(f"最高 GC        : {max(stats['gc_rates']):.3f}%")
    print(f"最低 GC        : {min(stats['gc_rates']):.3f}%")
    print(f"最长同聚物     : {max(stats['max_homo'])}")
    print(f"约束通过率     : {success_rate:.2f}% ✓")
    print("结论：编码器在极端条件下依然100%满足拟南芥级生物约束！")
    print("可安全用于真实DNA存储实验与合成！")
    print("=" * 80)

    return True, stats


# ==============================
# 一键运行终极测试
# ==============================
if __name__ == "__main__":
    # 先跑 100 轮快速验证（10秒内）
    print("阶段1：快速验证（100轮）")
    success, _ = stress_test(rounds=100, min_size=100, max_size=2000)

    if success:
        print("\n快速验证通过！即将进入终极10000轮压力测试……")
        import time

        time.sleep(2)
        stress_test(rounds=10000, min_size=50, max_size=5000)
    else:
        print("快速验证失败，请检查编码器逻辑")