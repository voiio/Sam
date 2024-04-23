from sam.utils import AssistantConfig


class TestAssistantConfig:
    def test_system_prompt(self):
        assert (
            AssistantConfig(
                name="Test",
                assistant_id="test",
                project="test",
                instructions=["tests/fixtures/harry.md", "tests/fixtures/security.md"],
            ).system_prompt
            == "You are a wizard, Harry.\n\nYou mustn't tell lies.\n"
        )
