# Importa as classes do seu arquivo de node
from .character_selector import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

# Exporta os mapeamentos para que o ComfyUI possa usá-los
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']