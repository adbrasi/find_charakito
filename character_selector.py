import os
import random

# Classe principal do Node
class RandomCharacterSelector:
    """
    Um node customizado para o ComfyUI que seleciona aleatoriamente um personagem
    de um arquivo de texto, com filtros opcionais por gênero (1girl/1boy) e quantidade.
    """

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        """
        Define os inputs que o usuário verá na interface do ComfyUI.
        """
        # Pega o caminho do diretório onde este script está localizado
        p_dir = os.path.dirname(os.path.realpath(__file__))
        # O arquivo de personagens deve estar na mesma pasta
        s.character_file = os.path.join(p_dir, "character.txt")
        
        return {
            "required": {
                "gender_filter": (["any", "girl", "boy"],),
                # NOVO INPUT: Filtro de quantidade
                # "INT" para um campo de número inteiro.
                # default: 0 (significa sem limite)
                # min: 0 (não pode ser negativo)
                # max: um número bem grande para não limitar na prática
                # step: o incremento ao usar as setas
                "quantity_limit": ("INT", {
                    "default": 0, 
                    "min": 0, 
                    "max": 1000000, 
                    "step": 10
                }),
            },
        }

    # Define os tipos de dados que o node vai retornar
    RETURN_TYPES = ("STRING", "STRING")
    # Define os nomes das saídas (outputs)
    RETURN_NAMES = ("character_name", "full_tags")

    # Define a função principal que será executada
    FUNCTION = "select_character"

    # Define a categoria onde o node aparecerá no menu do ComfyUI
    CATEGORY = "Utils/Selectors"

    # A assinatura da função agora inclui o novo parâmetro 'quantity_limit'
    def select_character(self, gender_filter, quantity_limit):
        """
        Lê o arquivo, aplica os filtros e seleciona um personagem aleatoriamente.
        """
        try:
            with open(self.character_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except FileNotFoundError:
            print(f"Aviso: Arquivo de personagem não encontrado em {self.character_file}")
            return ("", "")

        # Remove linhas em branco e espaços extras
        all_characters = [line.strip() for line in lines if line.strip()]

        if not all_characters:
            print("Aviso: O arquivo de personagens está vazio.")
            return ("", "")
        
        # --- LÓGICA ATUALIZADA ---
        
        # 1. Aplica o filtro de quantidade PRIMEIRO
        # Se quantity_limit for maior que 0, pega apenas as primeiras N linhas.
        # Caso contrário (se for 0), usa a lista inteira.
        if quantity_limit > 0:
            potential_characters = all_characters[:quantity_limit]
        else:
            potential_characters = all_characters

        # 2. Aplica o filtro de gênero na lista já reduzida
        filtered_characters = []
        if gender_filter == "any":
            filtered_characters = potential_characters
        elif gender_filter == "girl":
            filtered_characters = [char for char in potential_characters if "1girl" in char]
        elif gender_filter == "boy":
            filtered_characters = [char for char in potential_characters if "1boy" in char]

        # Se nenhum personagem corresponder aos filtros combinados, retorna vazio
        if not filtered_characters:
            print(f"Aviso: Nenhum personagem encontrado para os filtros: Gênero='{gender_filter}', Limite='{quantity_limit}'.")
            return ("", "")

        # 3. Escolhe um personagem aleatoriamente da lista final
        selected_line = random.choice(filtered_characters)
        
        # A linha completa são as "full_tags"
        full_tags = selected_line

        # O nome do personagem é a primeira tag, antes da primeira vírgula
        character_name = selected_line.split(',', 1)[0]

        # Retorna o nome e as tags completas
        return (character_name, full_tags)


# Mapeamento para o ComfyUI reconhecer o node
NODE_CLASS_MAPPINGS = {
    "RandomCharacterSelector": RandomCharacterSelector
}

# Mapeamento para o nome que aparecerá na interface
NODE_DISPLAY_NAME_MAPPINGS = {
    "RandomCharacterSelector": "Random charakito Selector"
}