import sys

from src.prompt_builder import PromptBuilder

class GUIWrapper:
    def __init__(self, prompt: str):
        self.prompt_builder = PromptBuilder(prompt)

    def run(self):
        # Logic to run the GUI and integrate with the CLI
        print("Running GUI with CLI integration...")
        # Example: Call methods from PromptBuilder to use within GUI
        self.prompt_builder.build_prompt()  # Adjust parameters as needed

if __name__ == '__main__':
    if len(sys.argv) > 1:
        prompt = sys.argv[1]
    else:
        prompt = "Default prompt"
    gui = GUIWrapper(prompt)
    gui.run()