# ComfyUI

## Sample workflows

* [civitai link](https://civitai.com/images/86482829)
  * [workflow.json](workflow.json)
  * [workflow_advanced.json](workflow_advanced.json)

## Pointers

* ComfyUI-Manager
  * Config file path: ComfyUI/user/default/ComfyUI-Manager/config.ini
* [Wiki](https://comfyui-wiki.com/en)
* Installing comfyui, there is multiple options, use `comfy-cli`, which seems most reliable
  ```
  mkdir comfyui # Or another dir as the parent dir to install comfyui
  cd comfyui
  python3 -m venv comfy-env
  source comfy-env/bin/activate
  pip install comfy-cli
  comfy install # Install comfyui and comfyui-manager
  ```

## Key concepts

* **Nodes:** Individual functions (e.g., Load Checkpoint, KSampler) that are the building blocks of a workflow.
* **Workflows:** A graph or flowchart of connected nodes that defines the entire image generation process.
* **Procedural:** The process is broken down into a series of visual, sequential steps.
* **Modular:** Nodes can be easily swapped in and out to change the pipeline.
* **Data Flow:** Information (e.g., latent images, text prompts) travels from one node's output to another's input.
* **Execution Caching:** Only nodes with changed inputs or parameters are re-run, saving time and resources.
* **Customization:** The ability to add new functionality through community-made custom nodes.
* **Workflows in PNGs:** The entire workflow metadata is saved directly within the generated image file, allowing for easy sharing.

## Saving Images from ComfyUI

### Automatic Saving

* Images are automatically saved to `ComfyUI/output/` directory

* Filenames include timestamps and workflow information
* Parameters are embedded in PNG metadata

### Manual Saving

* Right-click on generated image in ComfyUI

* Select "Save Image"
* Choose your desired location

## Using Images in Automatic1111

ComfyUI and Automatic1111 use different parameter formats. Use the included converter script:

### Installation

```bash
pip install -r requirements.txt
```

### Single Image Conversion

```bash
python comfyui_to_automatic1111.py path/to/comfyui_image.png
```

### Batch Conversion

```bash
python comfyui_to_automatic1111.py --batch ComfyUI/output/
```

### What the Converter Does

1. **Extracts** ComfyUI parameters from PNG metadata
2. **Converts** them to Automatic1111 format
3. **Saves** new images with A1111-compatible parameters
4. **Creates** `automatic1111_ready/` directory with converted images

### Using Converted Images in A1111

1. Copy images from `automatic1111_ready/` to your A1111 `outputs/` directory
2. Open A1111 and go to the "PNG Info" tab
3. Load any converted image to see the parameters
4. Click "Send to txt2img" or "Send to img2img" to use the parameters

## References

1. [key concepts](https://g.co/gemini/share/f5ea8079380c)
