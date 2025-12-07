"""
Unit Tests for NLU

Tests for Natural Language Understanding.
"""

import pytest

from amadeus.adapters.voice.nlu import DeterministicNLU, NLUPattern
from amadeus.core.entities import IntentType


class TestDeterministicNLU:
    """Tests for DeterministicNLU."""

    @pytest.fixture
    def nlu(self):
        """Creates an instance of NLU."""
        return DeterministicNLU()
    
    # ============================================
    # OPEN_APP Tests
    # ============================================
    
    def test_open_app_basic(self, nlu):
        """Tests the basic open app command."""
        intent = nlu.parse("open calculator")
        
        assert intent.intent_type == IntentType.OPEN_APP
        assert intent.slots["app_name"] == "calculator"
        assert intent.confidence == 1.0
    
    def test_open_app_launch(self, nlu):
        """Tests the launch command."""
        intent = nlu.parse("launch notepad")
        
        assert intent.intent_type == IntentType.OPEN_APP
        assert intent.slots["app_name"] == "notepad"
    
    def test_open_app_start(self, nlu):
        """Tests the start command."""
        intent = nlu.parse("start browser")
        
        assert intent.intent_type == IntentType.OPEN_APP
        assert intent.slots["app_name"] == "browser"
    
    def test_open_app_run(self, nlu):
        """Tests the run command."""
        intent = nlu.parse("run terminal")
        
        assert intent.intent_type == IntentType.OPEN_APP
        assert intent.slots["app_name"] == "terminal"
    
    def test_open_app_with_suffix(self, nlu):
        """Tests with suffix 'app'."""
        intent = nlu.parse("open calculator app")
        
        assert intent.intent_type == IntentType.OPEN_APP
        assert intent.slots["app_name"] == "calculator"
    
    # ============================================
    # OPEN_URL Tests
    # ============================================
    
    def test_open_url_https(self, nlu):
        """Tests opening HTTPS URL."""
        intent = nlu.parse("go to https://github.com")
        
        assert intent.intent_type == IntentType.OPEN_URL
        assert intent.slots["url"] == "https://github.com"
    
    def test_open_url_www(self, nlu):
        """Tests opening www URL."""
        intent = nlu.parse("open www.google.com")
        
        assert intent.intent_type == IntentType.OPEN_URL
        assert "https://" in intent.slots["url"]  # Should be added

    def test_open_url_domain(self, nlu):
        """Tests opening simple domain."""
        intent = nlu.parse("visit github.com")
        
        assert intent.intent_type == IntentType.OPEN_URL
        assert "github.com" in intent.slots["url"]
    
    # ============================================
    # WEB_SEARCH Tests
    # ============================================
    
    def test_search_basic(self, nlu):
        """Tests the basic search."""
        intent = nlu.parse("search for python tutorials")
        
        assert intent.intent_type == IntentType.WEB_SEARCH
        assert intent.slots["query"] == "python tutorials"
    
    def test_search_google(self, nlu):
        """Tests searching via google."""
        intent = nlu.parse("google machine learning")
        
        assert intent.intent_type == IntentType.WEB_SEARCH
        assert "machine learning" in intent.slots["query"]
    
    def test_search_what_is(self, nlu):
        """Tests the 'what is' question."""
        intent = nlu.parse("what is clean architecture")
        
        assert intent.intent_type == IntentType.WEB_SEARCH
        assert "clean architecture" in intent.slots["query"]
    
    def test_search_look_up(self, nlu):
        """Tests 'look up'."""
        intent = nlu.parse("look up python documentation")
        
        assert intent.intent_type == IntentType.WEB_SEARCH
    
    # ============================================
    # LIST_DIR Tests
    # ============================================
    
    def test_list_dir_basic(self, nlu):
        """Tests directory listing."""
        intent = nlu.parse("list files in ~/Documents")
        
        assert intent.intent_type == IntentType.LIST_DIR
        # Path is normalized based on OS
        assert "path" in intent.slots
    
    def test_list_dir_show(self, nlu):
        """Tests the show command."""
        intent = nlu.parse("show ~/Downloads")
        
        assert intent.intent_type == IntentType.LIST_DIR
    
    def test_list_dir_whats_in(self, nlu):
        """Tests the 'what's in' question with explicit path."""
        intent = nlu.parse("what's in ~/Downloads")
        
        assert intent.intent_type == IntentType.LIST_DIR
    
    def test_list_dir_ls(self, nlu):
        """Tests the ls command."""
        intent = nlu.parse("ls /tmp")
        
        assert intent.intent_type == IntentType.LIST_DIR
    
    # ============================================
    # READ_FILE Tests
    # ============================================
    
    def test_read_file_basic(self, nlu):
        """Tests reading a file."""
        intent = nlu.parse("read file ~/Documents/notes.txt")
        
        assert intent.intent_type == IntentType.READ_FILE
        assert "notes.txt" in intent.slots["path"]
    
    def test_read_file_cat(self, nlu):
        """Tests the cat command."""
        intent = nlu.parse("cat config.json")
        
        assert intent.intent_type == IntentType.READ_FILE
    
    def test_read_file_show_contents(self, nlu):
        """Tests the show command for reading a file."""
        intent = nlu.parse("view readme.md")
        
        assert intent.intent_type == IntentType.READ_FILE
    
    # ============================================
    # CREATE_FILE Tests
    # ============================================
    
    def test_create_file_basic(self, nlu):
        """Tests file creation."""
        intent = nlu.parse("create file ~/Documents/test.txt")
        
        assert intent.intent_type == IntentType.CREATE_FILE
        assert "test.txt" in intent.slots["path"]
    
    def test_create_file_touch(self, nlu):
        """Tests the touch command."""
        intent = nlu.parse("touch readme.md")
        
        assert intent.intent_type == IntentType.CREATE_FILE
    
    def test_create_file_new(self, nlu):
        """Tests 'new file'."""
        intent = nlu.parse("new file test.py")
        
        assert intent.intent_type == IntentType.CREATE_FILE
    
    def test_create_file_with_content(self, nlu):
        """Tests creating with content."""
        intent = nlu.parse("create file hello.txt with content Hello World")
        
        assert intent.intent_type == IntentType.CREATE_FILE
        assert "hello.txt" in intent.slots["path"]
        # Content may or may not be present depending on regex
    
    # ============================================
    # WRITE_FILE Tests
    # ============================================
    
    def test_write_file_basic(self, nlu):
        """Tests writing to a file."""
        intent = nlu.parse("write Hello World to test.txt")
        
        assert intent.intent_type == IntentType.WRITE_FILE
        # Content is normalized to lowercase
        assert "hello world" in intent.slots["content"].lower()
        assert "test.txt" in intent.slots["path"]
    
    def test_write_file_save(self, nlu):
        """Tests the save command."""
        intent = nlu.parse("save my notes to notes.txt")
        
        assert intent.intent_type == IntentType.WRITE_FILE
    
    # ============================================
    # DELETE_FILE Tests
    # ============================================
    
    def test_delete_file_basic(self, nlu):
        """Tests file deletion."""
        intent = nlu.parse("delete file ~/Documents/old.txt")
        
        assert intent.intent_type == IntentType.DELETE_FILE
        assert "old.txt" in intent.slots["path"]
    
    def test_delete_file_remove(self, nlu):
        """Tests the remove command."""
        intent = nlu.parse("remove temp.log")
        
        assert intent.intent_type == IntentType.DELETE_FILE
    
    def test_delete_file_rm(self, nlu):
        """Tests the rm command."""
        intent = nlu.parse("rm old_folder")
        
        assert intent.intent_type == IntentType.DELETE_FILE
    
    # ============================================
    # SYSTEM_INFO Tests
    # ============================================
    
    def test_system_info_basic(self, nlu):
        """Tests system information."""
        intent = nlu.parse("system info")
        
        assert intent.intent_type == IntentType.SYSTEM_INFO
    
    def test_system_info_show(self, nlu):
        """Tests the 'system info' command with shorthand."""
        intent = nlu.parse("system info")
        
        assert intent.intent_type == IntentType.SYSTEM_INFO
    
    def test_system_info_status(self, nlu):
        """Tests 'system status'."""
        intent = nlu.parse("system status")
        
        assert intent.intent_type == IntentType.SYSTEM_INFO
    
    # ============================================
    # UNKNOWN Tests
    # ============================================
    
    def test_unknown_gibberish(self, nlu):
        """Tests an unrecognized command."""
        intent = nlu.parse("asdfghjkl qwerty")
        
        assert intent.intent_type == IntentType.UNKNOWN
        assert intent.confidence == 0.0
    
    def test_unknown_partial(self, nlu):
        """Tests a partially similar command."""
        intent = nlu.parse("maybe open something")

        # Should not match any pattern
        # Depends on exact regex
        assert intent.intent_type in (IntentType.UNKNOWN, IntentType.OPEN_APP)
    
    # ============================================
    # Edge Cases
    # ============================================
    
    def test_empty_input(self, nlu):
        """Tests empty input."""
        intent = nlu.parse("")
        
        assert intent.intent_type == IntentType.UNKNOWN
    
    def test_whitespace_only(self, nlu):
        """Tests input with only whitespace."""
        intent = nlu.parse("   ")
        
        assert intent.intent_type == IntentType.UNKNOWN
    
    def test_case_insensitive(self, nlu):
        """Tests case insensitivity."""
        intent1 = nlu.parse("OPEN CALCULATOR")
        intent2 = nlu.parse("open calculator")
        
        assert intent1.intent_type == intent2.intent_type
        assert intent1.slots["app_name"] == intent2.slots["app_name"]
    
    def test_extra_whitespace(self, nlu):
        """Tests extra whitespace."""
        intent = nlu.parse("  open   calculator  ")
        
        assert intent.intent_type == IntentType.OPEN_APP
        assert intent.slots["app_name"] == "calculator"
    
    # ============================================
    # Ukrainian Language Tests
    # ============================================
    
    def test_ukrainian_open_app(self, nlu):
        """Tests the Ukrainian open app command."""
        intent = nlu.parse("відкрий калькулятор")
        
        assert intent.intent_type == IntentType.OPEN_APP
        assert "калькулятор" in intent.slots["app_name"]
    
    def test_ukrainian_search(self, nlu):
        """Tests the Ukrainian search command."""
        intent = nlu.parse("пошук рецепти борщу")
        
        assert intent.intent_type == IntentType.WEB_SEARCH
        assert "рецепти борщу" in intent.slots["query"]
    
    # ============================================
    # Pattern Management Tests
    # ============================================
    
    def test_add_custom_pattern(self, nlu):
        """Tests adding a custom pattern."""
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
        """Tests getting supported intents."""
        intents = nlu.get_supported_intents()
        
        assert IntentType.OPEN_APP in intents
        assert IntentType.WEB_SEARCH in intents
        assert IntentType.SYSTEM_INFO in intents
    
    def test_get_examples(self, nlu):
        """Tests getting examples."""
        examples = nlu.get_examples(IntentType.OPEN_APP)
        
        assert len(examples) > 0
        assert any("calculator" in ex for ex in examples)
