"""
comfyui_character_tags_node.py
Nó ComfyUI para selecionar personagem aleatório e buscar suas tags no Danbooru.
"""

import os
import random
import asyncio
from typing import Tuple, List, Optional
import aiohttp
from bs4 import BeautifulSoup
from collections import Counter, defaultdict

# --- Configurações do Scraper ----------------------------------------------

UA = "Mozilla/5.0 (compatible; TagScraper/1.0; +https://github.com/)"
MAX_CONCURRENT = 10
TIMEOUT = 15
RETRIES = 3
RATE_LIMIT = 0.1

# Categorias de tags
TAG_CATEGORIES = {
    'hair_details': {
        'bangs', 'ponytail', 'twintails', 'braid', 'drill_hair', 'ahoge',
        'sidelocks', 'hair_bun', 'short_hair', 'long_hair', 'medium_hair',
        'wavy_hair', 'curly_hair', 'straight_hair', 'messy_hair'
    },
    'hair_accessories': {
        'hair_ornament', 'hairband', 'hair_ribbon', 'hair_bow', 'hairclip',
        'hair_flower', 'headband', 'hair_tie', 'scrunchie'
    },
    'eye_features': {
        'eyes', 'heterochromia', 'eye_contact', 'closed_eyes', 'one_eye_closed',
        'eyeshadow', 'eyelashes', 'slit_pupils', 'heart-shaped_pupils'
    },
    'clothing_upper': {
        'shirt', 'jacket', 'coat', 'sweater', 'dress', 'uniform', 'hoodie',
        'vest', 'cape', 'blouse', 'top', 'bodysuit', 'leotard'
    },
    'clothing_lower': {
        'skirt', 'pants', 'shorts', 'jeans', 'trousers', 'leggings',
        'pantyhose', 'thighhighs', 'stockings', 'socks'
    },
    'accessories': {
        'bow', 'ribbon', 'necktie', 'bowtie', 'scarf', 'belt', 'gloves',
        'bracelet', 'ring', 'watch', 'glasses', 'sunglasses', 'eyewear'
    },
    'headwear': {
        'hat', 'cap', 'beret', 'crown', 'tiara', 'helmet', 'hood',
        'headphones', 'ear_covers'
    },
    'jewelry': {
        'earrings', 'necklace', 'pendant', 'choker', 'chain', 'piercing'
    },
    'special_features': {
        'wings', 'tail', 'horns', 'animal_ears', 'fang', 'pointy_ears',
        'demon_tail', 'demon_horns', 'angel_wings', 'fairy_wings'
    }
}

BLACKLIST_TAGS = {
    'solo', 'simple_background', 'white_background', 'looking_at_viewer',
    'smile', 'open_mouth', 'highres', 'absurdres', 'commentary', 'english_commentary',
    'artist_name', 'signature', 'watermark', 'username', 'dated', 'twitter_username',
    'pixiv_id', 'bad_id', 'bad_pixiv_id', 'duplicate', 'md5_mismatch',
    'multiple_views', 'comic', 'translation_request', 'commentary_request'
}

import re
EXCLUDED_PATTERNS = [
    re.compile(r'^(?!1)\d+(girl|boy)s?$'),
    re.compile(r'^\d+koma$'),
    re.compile(r'^(very_)?(high|low)res$'),
    re.compile(r'^(un)?censored$'),
    re.compile(r'^rating_[qse]$'),
]

# --- Classes do Scraper (versão simplificada) -----------------------------

class AsyncDanbooruClient:
    def __init__(self):
        self.session = None
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        
    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=TIMEOUT)
        self.session = aiohttp.ClientSession(
            headers={'User-Agent': UA},
            timeout=timeout
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def fetch_page(self, url: str, retries: int = RETRIES) -> str:
        async with self._semaphore:
            for attempt in range(retries):
                try:
                    await asyncio.sleep(RATE_LIMIT)
                    async with self.session.get(url) as response:
                        response.raise_for_status()
                        return await response.text()
                except Exception:
                    if attempt == retries - 1:
                        return ""
                    await asyncio.sleep(2 ** attempt)
        return ""

class TagProcessor:
    def __init__(self, character_tag: str):
        self.character_tag = character_tag
        self.tag_counter = Counter()
        self.tag_positions = defaultdict(list)
        
    def is_excluded(self, tag: str) -> bool:
        if tag in BLACKLIST_TAGS:
            return True
        if tag == self.character_tag:
            return True
        return any(pattern.match(tag) for pattern in EXCLUDED_PATTERNS)
    
    def categorize_tag(self, tag: str) -> Optional[str]:
        for category, keywords in TAG_CATEGORIES.items():
            if any(keyword in tag for keyword in keywords):
                return category
        return None
    
    def process_raw_tags(self, tags_raw: List[str]) -> None:
        for i, raw in enumerate(tags_raw):
            tags = raw.split()
            for j, tag in enumerate(tags):
                if not self.is_excluded(tag):
                    self.tag_counter[tag] += 1
                    self.tag_positions[tag].append(j)
    
    def get_gender_tag(self, threshold: float = 0.8) -> Optional[str]:
        if not self.tag_positions:
            return None
        total_images = len(set(i for positions in self.tag_positions.values() for i in range(len(positions))))
        for gender in ["1girl", "1boy"]:
            if gender in self.tag_counter:
                freq = self.tag_counter[gender] / max(total_images, 1)
                if freq >= threshold:
                    return gender
        return None
    
    def get_consistent_tags(self, min_frequency: float = 0.5) -> dict:
        if not self.tag_positions:
            return {}
            
        total_images = len(set(i for positions in self.tag_positions.values() for i in range(len(positions))))
        consistent = {}
        
        for tag, count in self.tag_counter.items():
            frequency = count / max(total_images, 1)
            if frequency >= min_frequency and not self.is_excluded(tag):
                avg_position = sum(self.tag_positions[tag]) / len(self.tag_positions[tag])
                position_score = 1 / (1 + avg_position * 0.1)
                consistent[tag] = frequency * position_score
                
        return consistent
    
    def select_best_tags(self, consistent_tags: dict, max_tags: int = 10) -> List[str]:
        categorized = defaultdict(list)
        uncategorized = []
        
        for tag, score in sorted(consistent_tags.items(), key=lambda x: x[1], reverse=True):
            category = self.categorize_tag(tag)
            if category:
                categorized[category].append((tag, score))
            else:
                uncategorized.append((tag, score))
        
        selected = []
        category_limits = {
            'hair_details': 2,
            'hair_accessories': 1,
            'eye_features': 2,
            'clothing_upper': 2,
            'clothing_lower': 1,
            'accessories': 2,
            'headwear': 1,
            'jewelry': 1,
            'special_features': 2
        }
        
        for category, limit in category_limits.items():
            if category in categorized:
                selected.extend([tag for tag, _ in categorized[category][:limit]])
        
        remaining = max_tags - len(selected)
        if remaining > 0:
            selected.extend([tag for tag, _ in uncategorized[:remaining]])
        
        return selected[:max_tags]

# --- Funções do Scraper ---------------------------------------------------

async def scrape_page_async(client: AsyncDanbooruClient, tag: str, page: int) -> List[str]:
    url = f"https://danbooru.donmai.us/posts?page={page}&tags={tag}"
    html = await client.fetch_page(url)
    
    if not html:
        return []
    
    soup = BeautifulSoup(html, "lxml")
    return [
        art.get("data-tags", "")
        for art in soup.select("div.posts-container.gap-2 > article")
        if art.get("data-tags")
    ]

async def scrape_booru_async(tag: str, num_pages: int = 3) -> List[str]:
    async with AsyncDanbooruClient() as client:
        tasks = [
            scrape_page_async(client, tag, page)
            for page in range(1, num_pages + 1)
        ]
        results = await asyncio.gather(*tasks)
        
    return [tags for page_tags in results for tags in page_tags]

async def get_character_details_async(character_tag: str, pages: int = 3) -> Tuple[Optional[str], str]:
    """Retorna (gender, tags) para o personagem."""
    try:
        raw_tags = await scrape_booru_async(character_tag, pages)
        
        if not raw_tags:
            return None, ""
        
        processor = TagProcessor(character_tag)
        processor.process_raw_tags(raw_tags)
        
        gender_tag = processor.get_gender_tag()
        consistent = processor.get_consistent_tags(0.5)
        best_tags = processor.select_best_tags(consistent)
        
        # Remove gender tag da lista final se existir
        final_tags = [tag for tag in best_tags if tag not in ["1girl", "1boy"]]
        
        return gender_tag, ", ".join(dict.fromkeys(final_tags))
    except Exception as e:
        print(f"Erro ao buscar dados para {character_tag}: {e}")
        return None, ""

# --- Nó ComfyUI -----------------------------------------------------------

class RandomCharacterTags:
    """
    Nó ComfyUI que seleciona um personagem aleatório e busca suas tags.
    """
    
    def __init__(self):
        self.characters_file = os.path.join(os.path.dirname(__file__), "characters_list.txt")
        self._characters_cache = None
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "gender_filter": (["any", "girl", "boy"],),
                "pages_to_search": ("INT", {
                    "default": 3,
                    "min": 1,
                    "max": 10,
                    "step": 1,
                    "display": "number"
                }),
                "seed": ("INT", {
                    "default": -1,
                    "min": -1,
                    "max": 0xffffffffffffffff,
                    "display": "number"
                }),
            },
        }
    
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("character_name", "character_tags")
    FUNCTION = "get_random_character"
    CATEGORY = "utils/character"
    
    def load_characters(self) -> List[str]:
        """Carrega a lista de personagens do arquivo."""
        if self._characters_cache is None:
            try:
                with open(self.characters_file, 'r', encoding='utf-8') as f:
                    self._characters_cache = [line.strip() for line in f if line.strip()]
            except FileNotFoundError:
                print(f"Erro: Arquivo {self.characters_file} não encontrado!")
                self._characters_cache = []
            except Exception as e:
                print(f"Erro ao ler arquivo de personagens: {e}")
                self._characters_cache = []
        
        return self._characters_cache
    
    def get_random_character(self, gender_filter: str, pages_to_search: int, seed: int) -> Tuple[str, str]:
        """
        Seleciona um personagem aleatório e busca suas tags.
        """
        characters = self.load_characters()
        
        if not characters:
            return ("", "")
        
        # Define seed para reprodutibilidade
        if seed != -1:
            random.seed(seed)
        
        # Tenta até 10 vezes encontrar um personagem com o gênero correto
        max_attempts = 10
        for _ in range(max_attempts):
            character = random.choice(characters)
            
            # Executa a busca assíncrona
            try:
                # Cria novo event loop se necessário
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                gender, tags = loop.run_until_complete(
                    get_character_details_async(character, pages_to_search)
                )
                
                # Verifica o filtro de gênero
                if gender_filter == "any":
                    return (character, tags)
                elif gender_filter == "girl" and gender == "1girl":
                    return (character, tags)
                elif gender_filter == "boy" and gender == "1boy":
                    return (character, tags)
                
            except Exception as e:
                print(f"Erro ao processar {character}: {e}")
                continue
        
        # Se não encontrou após todas as tentativas
        return ("", "No matching character found")

# --- Registro do nó -------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "RandomCharacterTags": RandomCharacterTags
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RandomCharacterTags": "Find Random charakito Tags bumbumsujo"
}


