"""
サイト用の派生画像を生成する（元素材から一度だけ作ればよい）

  python scripts/build_assets.py

入力: assets/images/logo.jpg   （プロフィール画像・正方形）
      assets/images/ogp.jpg    （ヘッダー画像・正方形）
出力: favicon-32.png / favicon-180.png / og-image.jpg
"""

import os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "assets", "images")


def make_favicons(src_path):
    src = Image.open(src_path).convert("RGB")
    for size in (32, 180):
        out = os.path.join(IMG, f"favicon-{size}.png")
        src.resize((size, size), Image.LANCZOS).save(out, optimize=True)
        print("saved", os.path.basename(out))


def make_ogp(src_path, width=1200, height=630):
    """OGPの推奨比率(1.91:1)に中央基準で切り出す"""
    src = Image.open(src_path).convert("RGB")
    target_ratio = width / height
    w, h = src.size
    if w / h > target_ratio:            # 横長すぎる → 左右を削る
        new_w = int(h * target_ratio)
        box = ((w - new_w) // 2, 0, (w - new_w) // 2 + new_w, h)
    else:                                # 縦長すぎる → 上下を削る
        new_h = int(w / target_ratio)
        top = int((h - new_h) * 0.35)    # 中央よりやや上（筆先が入るように）
        box = (0, top, w, top + new_h)
    out = os.path.join(IMG, "og-image.jpg")
    src.crop(box).resize((width, height), Image.LANCZOS).save(out, quality=88, optimize=True)
    print("saved", os.path.basename(out))


if __name__ == "__main__":
    make_favicons(os.path.join(IMG, "logo.jpg"))
    make_ogp(os.path.join(IMG, "ogp.jpg"))
