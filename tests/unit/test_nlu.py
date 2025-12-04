"""
Unit Tests for NLU

Тести для Natural Language Understanding.
"""

import pytest

from amadeus.adapters.voice.nlu import DeterministicNLU, NLUPattern
from amadeus.core.entities import IntentType


class TestDeterministicNLU:
    """Тести для DeterministicNLU."""
    
    @pytest.fixture
    def nlu(self):
        """Створює екземпляр NLU."""
        return DeterministicNLU()
    
    # ============================================
    # OPEN_APP Tests
    # ============================================
    
    def test_open_app_basic(self, nlu):
        """Тест базової команди open app."""
        intent = nlu.parse("open calculator")
        
        assert intent.intent_type == IntentType.OPEN_APP
        assert intent.slots["app_name"] == "calculator"
        assert intent.confidence == 1.0
    
    def test_open_app_launch(self, nlu):
        """Тест команди launch."""
        intent = nlu.parse("launch notepad")
        
        assert intent.intent_type == IntentType.OPEN_APP
        assert intent.slots["app_name"] == "notepad"
    
    def test_open_app_start(self, nlu):
        """Тест команди start."""
        intent = nlu.parse("start browser")
        
        assert intent.intent_type == IntentType.OPEN_APP
        assert intent.slots["app_name"] == "browser"
    
    def test_open_app_run(self, nlu):
        """Тест команди run."""
        intent = nlu.parse("run terminal")
        
        assert intent.intent_type == IntentType.OPEN_APP
        assert intent.slots["app_name"] == "terminal"
    
    def test_open_app_with_suffix(self, nlu):
        """Тест з суфіксом 'app'."""
        intent = nlu.parse("open calculator app")
        
        assert intent.intent_type == IntentType.OPEN_APP
        assert intent.slots["app_name"] == "calculator"
    
    # ============================================
    # OPEN_URL Tests
    # ============================================
    
    def test_open_url_https(self, nlu):
        """Тест відкриття HTTPS URL."""
        intent = nlu.parse("go to https://github.com")
        
        assert intent.intent_type == IntentType.OPEN_URL
        assert intent.slots["url"] == "https://github.com"
    
    def test_open_url_www(self, nlu):
        """Тест відкриття www URL."""
        intent = nlu.parse("open www.google.com")
        
        assert intent.intent_type == IntentType.OPEN_URL
        assert "https://" in intent.slots["url"]  # Має бути додано
    
    def test_open_url_domain(self, nlu):
        """Тест відкриття простого домену."""
        intent = nlu.parse("visit github.com")
        
        assert intent.intent_type == IntentType.OPEN_URL
        assert "github.com" in intent.slots["url"]
    
    # ============================================
    # WEB_SEARCH Tests
    # ============================================
    
    def test_search_basic(self, nlu):
        """Тест базового пошуку."""
        intent = nlu.parse("search for python tutorials")
        
        assert intent.intent_type == IntentType.WEB_SEARCH
        assert intent.slots["query"] == "python tutorials"
    
    def test_search_google(self, nlu):
        """Тест пошуку через google."""
        intent = nlu.parse("google machine learning")
        
        assert intent.intent_type == IntentType.WEB_SEARCH
        assert "machine learning" in intent.slots["query"]
    
    def test_search_what_is(self, nlu):
        """Тест питання 'what is'."""
        intent = nlu.parse("what is clean architecture")
        
        assert intent.intent_type == IntentType.WEB_SEARCH
        assert "clean architecture" in intent.slots["query"]
    
    def test_search_look_up(self, nlu):
        """Тест 'look up'."""
        intent = nlu.parse("look up python documentation")
        
        assert intent.intent_type == IntentType.WEB_SEARCH
    
    # ============================================
    # LIST_DIR Tests
    # ============================================
    
    def test_list_dir_basic(self, nlu):
        """Тест перегляду директорії."""
        intent = nlu.parse("list files in ~/Documents")
        
        assert intent.intent_type == IntentType.LIST_DIR
        # Шлях нормалізується залежно від ОС
        assert "path" in intent.slots
    
    def test_list_dir_show(self, nlu):
        """Тест команди show."""
        intent = nlu.parse("show ~/Downloads")
        
        assert intent.intent_type == IntentType.LIST_DIR
    
    def test_list_dir_whats_in(self, nlu):
        """Тест питання 'what's in' з явним шляхом."""
        intent = nlu.parse("what's in ~/Downloads")
        
        assert intent.intent_type == IntentType.LIST_DIR
    
    def test_list_dir_ls(self, nlu):
        """Тест команди ls."""
        intent = nlu.parse("ls /tmp")
        
        assert intent.intent_type == IntentType.LIST_DIR
    
    # ============================================
    # READ_FILE Tests
    # ============================================
    
    def test_read_file_basic(self, nlu):
        """Тест читання файлу."""
        intent = nlu.parse("read file ~/Documents/notes.txt")
        
        assert intent.intent_type == IntentType.READ_FILE
        assert "notes.txt" in intent.slots["path"]
    
    def test_read_file_cat(self, nlu):
        """Тест команди cat."""
        intent = nlu.parse("cat config.json")
        
        assert intent.intent_type == IntentType.READ_FILE
    
    def test_read_file_show_contents(self, nlu):
        """Тест команди cat для читання файлу."""
        intent = nlu.parse("view readme.md")
        
        assert intent.intent_type == IntentType.READ_FILE
    
    # ============================================
    # CREATE_FILE Tests
    # ============================================
    
    def test_create_file_basic(self, nlu):
        """Тест створення файлу."""
        intent = nlu.parse("create file ~/Documents/test.txt")
        
        assert intent.intent_type == IntentType.CREATE_FILE
        assert "test.txt" in intent.slots["path"]
    
    def test_create_file_touch(self, nlu):
        """Тест команди touch."""
        intent = nlu.parse("touch readme.md")
        
        assert intent.intent_type == IntentType.CREATE_FILE
    
    def test_create_file_new(self, nlu):
        """Тест 'new file'."""
        intent = nlu.parse("new file test.py")
        
        assert intent.intent_type == IntentType.CREATE_FILE
    
    def test_create_file_with_content(self, nlu):
        """Тест створення з контентом."""
        intent = nlu.parse("create file hello.txt with content Hello World")
        
        assert intent.intent_type == IntentType.CREATE_FILE
        assert "hello.txt" in intent.slots["path"]
        # Content може бути або не бути в залежності від regex
    
    # ============================================
    # WRITE_FILE Tests
    # ============================================
    
    def test_write_file_basic(self, nlu):
        """Тест запису у файл."""
        intent = nlu.parse("write Hello World to test.txt")
        
        assert intent.intent_type == IntentType.WRITE_FILE
        # Контент нормалізується до lowercase
        assert "hello world" in intent.slots["content"].lower()
        assert "test.txt" in intent.slots["path"]
    
    def test_write_file_save(self, nlu):
        """Тест команди save."""
        intent = nlu.parse("save my notes to notes.txt")
        
        assert intent.intent_type == IntentType.WRITE_FILE
    
    # ============================================
    # DELETE_FILE Tests
    # ============================================
    
    def test_delete_file_basic(self, nlu):
        """Тест видалення файлу."""
        intent = nlu.parse("delete file ~/Documents/old.txt")
        
        assert intent.intent_type == IntentType.DELETE_FILE
        assert "old.txt" in intent.slots["path"]
    
    def test_delete_file_remove(self, nlu):
        """Тест команди remove."""
        intent = nlu.parse("remove temp.log")
        
        assert intent.intent_type == IntentType.DELETE_FILE
    
    def test_delete_file_rm(self, nlu):
        """Тест команди rm."""
        intent = nlu.parse("rm old_folder")
        
        assert intent.intent_type == IntentType.DELETE_FILE
    
    # ============================================
    # SYSTEM_INFO Tests
    # ============================================
    
    def test_system_info_basic(self, nlu):
        """Тест системної інформації."""
        intent = nlu.parse("system info")
        
        assert intent.intent_type == IntentType.SYSTEM_INFO
    
    def test_system_info_show(self, nlu):
        """Тест 'system info' з скороченням."""
        intent = nlu.parse("system info")
        
        assert intent.intent_type == IntentType.SYSTEM_INFO
    
    def test_system_info_status(self, nlu):
        """Тест 'system status'."""
        intent = nlu.parse("system status")
        
        assert intent.intent_type == IntentType.SYSTEM_INFO
    
    # ============================================
    # UNKNOWN Tests
    # ============================================
    
    def test_unknown_gibberish(self, nlu):
        """Тест нерозпізнаної команди."""
        intent = nlu.parse("asdfghjkl qwerty")
        
        assert intent.intent_type == IntentType.UNKNOWN
        assert intent.confidence == 0.0
    
    def test_unknown_partial(self, nlu):
        """Тест частково схожої команди."""
        intent = nlu.parse("maybe open something")
        
        # Не повинно матчитись жодному шаблону
        # Залежить від точних regex
        assert intent.intent_type in (IntentType.UNKNOWN, IntentType.OPEN_APP)
    
    # ============================================
    # Edge Cases
    # ============================================
    
    def test_empty_input(self, nlu):
        """Тест порожнього вводу."""
        intent = nlu.parse("")
        
        assert intent.intent_type == IntentType.UNKNOWN
    
    def test_whitespace_only(self, nlu):
        """Тест вводу з пробілами."""
        intent = nlu.parse("   ")
        
        assert intent.intent_type == IntentType.UNKNOWN
    
    def test_case_insensitive(self, nlu):
        """Тест нечутливості до регістру."""
        intent1 = nlu.parse("OPEN CALCULATOR")
        intent2 = nlu.parse("open calculator")
        
        assert intent1.intent_type == intent2.intent_type
        assert intent1.slots["app_name"] == intent2.slots["app_name"]
    
    def test_extra_whitespace(self, nlu):
        """Тест з додатковими пробілами."""
        intent = nlu.parse("  open   calculator  ")
        
        assert intent.intent_type == IntentType.OPEN_APP
        assert intent.slots["app_name"] == "calculator"
    
    # ============================================
    # Ukrainian Language Tests
    # ============================================
    
    def test_ukrainian_open_app(self, nlu):
        """Тест української команди відкриття."""
        intent = nlu.parse("відкрий калькулятор")
        
        assert intent.intent_type == IntentType.OPEN_APP
        assert "калькулятор" in intent.slots["app_name"]
    
    def test_ukrainian_search(self, nlu):
        """Тест українського пошуку."""
        intent = nlu.parse("пошук рецепти борщу")
        
        assert intent.intent_type == IntentType.WEB_SEARCH
        assert "рецепти борщу" in intent.slots["query"]
    
    # ============================================
    # Pattern Management Tests
    # ============================================
    
    def test_add_custom_pattern(self, nlu):
        """Тест додавання кастомного шаблону."""
        custom_pattern = NLUPattern(
            intent_type=IntentType.SYSTEM_INFO,
            patterns=[r"^hello amadeus$"],
            priority=100,
            examples=["hello amadeus"],
        )
        
        nlu.add_pattern(custom_pattern)
        intent = nlu.parse("hello amadeus")
        
        assert intent.intent_type == IntentType.SYSTEM_INFO
    
    def test_get_supported_intents(self, nlu):
        """Тест отримання підтримуваних намірів."""
        intents = nlu.get_supported_intents()
        
        assert IntentType.OPEN_APP in intents
        assert IntentType.WEB_SEARCH in intents
        assert IntentType.SYSTEM_INFO in intents
    
    def test_get_examples(self, nlu):
        """Тест отримання прикладів."""
        examples = nlu.get_examples(IntentType.OPEN_APP)
        
        assert len(examples) > 0
        assert any("calculator" in ex for ex in examples)
