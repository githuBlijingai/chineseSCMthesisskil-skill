from __future__ import annotations

import json
import sys
from pathlib import Path


def validate_image_descriptions(image_registry: dict) -> list[str]:
    """验证每张图片都有足够的描述（≥50字）"""
    errors = []
    for img_id, img_info in image_registry.items():
        if isinstance(img_info, dict):
            desc = img_info.get("description", "")
            if len(desc) < 50:
                errors.append(f"图片 '{img_id}' 描述不足50字（当前{len(desc)}字）")
    return errors


def main() -> int:
    if len(sys.argv) < 4:
        print("Usage: python build_image_map.py <labels.json> <image-dir> <output.json> [--manual manual-map.json] [--registry registry.yaml]")
        return 1

    labels_path = Path(sys.argv[1])
    image_dir = Path(sys.argv[2])
    output_path = Path(sys.argv[3])
    manual_path = None
    registry_path = None
    
    # 解析可选参数
    i = 4
    while i < len(sys.argv):
        if sys.argv[i] == "--manual" and i + 1 < len(sys.argv):
            manual_path = Path(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--registry" and i + 1 < len(sys.argv):
            registry_path = Path(sys.argv[i + 1])
            i += 2
        else:
            i += 1

    labels = json.loads(labels_path.read_text(encoding="utf-8")).get("labels", [])
    manual_map = {}
    if manual_path and manual_path.exists():
        manual_map = json.loads(manual_path.read_text(encoding="utf-8"))
    
    # 构建图片映射
    result = {}
    for label in labels:
        if label in manual_map:
            manual_target = Path(manual_map[label])
            if manual_target.exists():
                result[label] = str(manual_target)
                continue
        candidates = [
            image_dir / f"{label}.png",
            image_dir / f"{label}.jpg",
            image_dir / f"{label}.jpeg",
        ]
        for candidate in candidates:
            if candidate.exists():
                result[label] = str(candidate)
                break

    # 如果有注册表，验证图片描述
    if registry_path and registry_path.exists():
        try:
            import yaml
            registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
            if registry and "images" in registry:
                errors = validate_image_descriptions(registry["images"])
                if errors:
                    print("[WARN] 图片描述验证未通过：")
                    for err in errors:
                        print(f"  - {err}")
                    print("[TIP] 请在 figure-registry.yaml 中为这些图片添加描述")
        except Exception as e:
            print(f"[WARN] 无法验证图片描述: {e}")

    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
