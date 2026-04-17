"""
将 .puml 文件编码为 PlantUML 在线服务 URL
使用方式：python3 generate_preview_links.py
然后在浏览器打开生成的链接即可预览/下载 PNG
"""
import zlib, base64, glob, os

PLANTUML_URL = "https://www.plantuml.com/plantuml/png/"

def encode_plantuml(text: str) -> str:
    data = text.encode("utf-8")
    compressed = zlib.compress(data)[2:-4]  # 去掉 zlib 头尾
    # PlantUML 用的是改版 base64（6bit 字符集不同）
    b64chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"
    std_b64 = base64.b64encode(compressed).decode("ascii")
    # 标准 base64 -> plantuml base64
    result = []
    for ch in std_b64:
        if ch == "+":
            result.append("-")
        elif ch == "/":
            result.append("_")
        elif ch == "=":
            result.append("=")
        else:
            result.append(ch)
    return "".join(result)

script_dir = os.path.dirname(os.path.abspath(__file__))
puml_files = sorted(glob.glob(os.path.join(script_dir, "*.puml")))

print("=" * 70)
print("PlantUML 在线预览链接（复制到浏览器打开即可查看/下载图片）")
print("=" * 70)
for fpath in puml_files:
    name = os.path.basename(fpath)
    with open(fpath, encoding="utf-8") as f:
        content = f.read()
    encoded = encode_plantuml(content)
    url = PLANTUML_URL + encoded
    print(f"\n[{name}]")
    print(f"  {url}")

print("\n" + "=" * 70)
print("提示：也可以直接在 VS Code 安装 'PlantUML' 插件后按 Alt+D 实时预览")
print("=" * 70)
