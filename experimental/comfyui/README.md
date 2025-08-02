# ComfyUI

## Sample workflows

* [civitai link](https://civitai.com/images/86482829)
  * [workflow.json](workflow.json)
  * [workflow_advanced.json](workflow_advanced.json)

## Pointers

* ComfyUI-Manager
  * Config file path: ComfyUI/user/default/ComfyUI-Manager/config.ini
* [Wiki](https://comfyui-wiki.com/en)

## Key concepts

* **Nodes:** Individual functions (e.g., Load Checkpoint, KSampler) that are the building blocks of a workflow.
* **Workflows:** A graph or flowchart of connected nodes that defines the entire image generation process.
* **Procedural:** The process is broken down into a series of visual, sequential steps.
* **Modular:** Nodes can be easily swapped in and out to change the pipeline.
* **Data Flow:** Information (e.g., latent images, text prompts) travels from one node's output to another's input.
* **Execution Caching:** Only nodes with changed inputs or parameters are re-run, saving time and resources.
* **Customization:** The ability to add new functionality through community-made custom nodes.
* **Workflows in PNGs:** The entire workflow metadata is saved directly within the generated image file, allowing for easy sharing.

## References

1. [key concepts](https://g.co/gemini/share/f5ea8079380c)
