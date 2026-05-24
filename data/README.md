# data/

Pipeline artifacts. Subfolders are gitignored so user uploads and renders never get committed.

| Folder | Contents |
|--------|----------|
| `uploads/` | Source videos uploaded via the frontend. |
| `frames/` | Frames extracted by the analysis pipeline (OpenCV / PySceneDetect). |
| `renders/` | Final mp4s rendered by Remotion + FFmpeg. |
| `knowledge_base/` | Saved `StructureCard` JSONs + any retrieval indexes. |

The `.gitkeep` files exist only so the directories are tracked.
