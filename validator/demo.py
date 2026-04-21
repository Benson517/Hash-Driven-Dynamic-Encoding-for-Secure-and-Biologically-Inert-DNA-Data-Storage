# from Bio import SeqIO
#
# # 读取 FASTA
# record = SeqIO.read("../拟南芥线粒体基因组/sequence.fasta", "fasta")
# # 提取 cox1 片段（300 bp，假设位置 12345-12645，需 GFF 确认）
# cox1_seq = str(record.seq[12345:12645])
# # 保存
# with open("cox1_short.fasta", "w") as f:
#     f.write(">cox1\n" + cox1_seq)
# print("Extracted sequence:", cox1_seq)

# 1. 定义文件路径和需提取的字符数
file_path = "image_dna_sequence.txt"  # 你的文件路径
target_length = 1065# 目标提取长度

# 2. 读取文件并截取前12295个字符
try:
    with open(file_path, "r", encoding="utf-8") as f:
        # read(target_length) 直接读取前 N 个字符
        first_12295_chars = f.read(target_length)

    # 3. 验证长度（可选，确保提取正确）
    actual_length = len(first_12295_chars)
    print(f"成功提取前 {actual_length} 个字符（目标：{target_length} 个）")

    # 4. 保存结果（可选，如需将提取内容另存为新文件）
    with open("first_12295_chars.txt", "w", encoding="utf-8") as output_f:
        output_f.write(first_12295_chars)
    print("提取结果已保存至 first_12295_chars.txt")

except FileNotFoundError:
    print(f"错误：未找到文件 {file_path}，请检查路径是否正确")

from skimage import io
from skimage.metrics import structural_similarity as ssim
import cv2

# 读取图像，确保它们是灰度图像
image1 = cv2.imread('1.png', cv2.IMREAD_GRAYSCALE)
image2 = cv2.imread('recovered_image_with_noise.png', cv2.IMREAD_GRAYSCALE)

# 计算 SSIM
ssim_index, _ = ssim(image1, image2, full=True)

# 打印 SSIM 值
print(f"SSIM: {ssim_index}")
