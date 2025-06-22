import os
import random

# Classe principal do Node
class RandomCharacterSelector:
    """
    Um node customizado para o ComfyUI que seleciona aleatoriamente um personagem
    de um arquivo de texto, com um filtro opcional por gênero (1girl/1boy).
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

    def select_character(self, gender_filter):
        """
        Lê o arquivo, filtra os personagens e seleciona um aleatoriamente.
        """
        try:
            with open(self.character_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except FileNotFoundError:
            print(f"Aviso: Arquivo de personagem não encontrado em {self.character_file}")
            return ("", "") # Retorna vazio se o arquivo não existir

        # Remove linhas em branco e espaços extras
        characters = [line.strip() for line in lines if line.strip()]

        if not characters:
            print("Aviso: O arquivo de personagens está vazio.")
            return ("", "")

        # Filtra a lista de personagens com base na seleção do usuário
        filtered_characters = []
        if gender_filter == "any":
            filtered_characters = characters
        elif gender_filter == "girl":
            filtered_characters = [char for char in characters if "1girl" in char]
        elif gender_filter == "boy":
            filtered_characters = [char for char in characters if "1boy" in char]

        # Se nenhum personagem corresponder ao filtro, retorna vazio
        if not filtered_characters:
            print(f"Aviso: Nenhum personagem encontrado para o filtro '{gender_filter}'.")
            return ("", "")

        # Escolhe um personagem aleatoriamente da lista filtrada
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
    "RandomCharacterSelector": "Random chrakito Selector"
}