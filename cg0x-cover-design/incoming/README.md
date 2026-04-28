# incoming/

新素材暂存区。

## 操作流程

1. 将新文件放入对应分组的子目录：

   ```
   incoming/{label}/新素材名称.png
   incoming/{label}/新素材名称.HumanCard.txt   （可选）
   incoming/{label}/新素材名称.Prompt.txt       （可选）
   ```

2. 切换到 skills repo，运行脚本：

   ```bash
   python tools/update_assets.py
   ```

脚本会自动：
- 识别新文件，分配 4 位随机 ID
- PNG → 移到 `showcase/cg0x-cover-design/{gid}/{fid}.png`
- 文本文件 → 移到 `skills/assets/{gid}/{fid}.HumanCard.txt` / `.Prompt.txt`
- 更新 `catalog.json`
- 重建 `README.md` 画廊章节

3. 提交两个 repo 的变更。

## Label 参考

| label | 描述 |
|---|---|
| `baroque` | 巴洛克 |
| `rococo` | 洛可可 |
| `mucha` | 慕夏·新艺术 |
| `klimt` | 克里姆特金色 |
| `bauhaus-mondrian` | 包豪斯·蒙德里安 |
| `guofeng` | 国风（宋画·水墨·自然） |
| `glass` | 玻璃材质 |
| `lo-fi` | 低保真·旧网页·像素 |
| `misc` | 其他 |

新 label 会自动创建新分组。
