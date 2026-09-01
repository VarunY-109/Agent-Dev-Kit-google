# Image Analysis Agent

A pure-Python ADK agent that performs **multimodal analysis** of
images. It works in two modes:

1. **Direct upload** - drop an image into the ADK web UI and the
   multimodal Gemini model (`gemini-2.0-flash`) can see it natively.
2. **Path-based** - point the agent at an image on disk; the agent
   uses the helper tools to read, resize and colour-quantise it
   before composing a description.

## Tools

| Tool | Purpose |
| --- | --- |
| `image_metadata(path)` | Width, height, mode, format, file size. |
| `load_image(path, max_dim=1024)` | Resize + base64-encode a preview for downstream calls. |
| `dominant_colors(path, n=5)` | Quantise the palette to the top *n* hex colours. |

> `Pillow` is used for image processing. If it isn't installed the
> example still runs, but the tools will return raw bytes without
> resizing and `dominant_colors` will refuse.

## Project Structure

```
17-image-analysis-agent/
└── image_analysis_agent/
    ├── __init__.py        # re-exports the agent
    ├── agent.py           # root_agent + image tools
    └── .env.example       # GOOGLE_API_KEY template
```

## Getting Started

1. Activate the root virtual environment:
   ```bash
   source ../.venv/bin/activate
   ```
2. (Optional) install Pillow for richer tools:
   ```bash
   pip install Pillow
   ```
3. Copy `.env.example` to `.env` and set `GOOGLE_API_KEY`.
4. Launch the UI:
   ```bash
   adk web
   ```
5. Select **image_analysis_agent** and either drag-and-drop an
   image or reference a local path.

## Example Prompts to Try

- Upload a screenshot of a dashboard and ask "What KPI trends do you
  see in this chart?"
- "Read the text in this image and translate it to French."
- "Analyse the image at /tmp/photo.jpg and give me a description
  plus the dominant 5 colours."
- "Compare the two images I uploaded and list 3 differences."
