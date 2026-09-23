import os
from crewai import LLM


class LLMFactory:
    """
    P1-B: Role-differentiated temperature factory.
    Different agent types require different temperatures:
    - creative (pm):           high temp for divergent market thinking
    - standard (ba/architect): balanced for structured analysis
    - auditor (nitpicker):     low temp for reproducible, strict reviews
    - operator (devops/qa):    minimal temp for deterministic tool execution

    All values can be overridden via environment variables.
    """

    _ROLE_TEMPS: dict[str, float] = {
        "creative":  float(os.getenv("LLM_TEMP_CREATIVE", "0.85")),
        "standard":  float(os.getenv("LLM_TEMP_STANDARD", "0.70")),
        "auditor":   float(os.getenv("LLM_TEMP_AUDITOR",  "0.15")),
        "operator":  float(os.getenv("LLM_TEMP_OPERATOR", "0.05")),
    }

    @staticmethod
    def create_llm(role_type: str = "standard") -> LLM:
        """
        Create an LLM instance with role-appropriate temperature.

        Args:
            role_type: One of 'creative', 'standard', 'auditor', 'operator'.
                       Defaults to 'standard' if unknown role_type is given.
        """
        temp = LLMFactory._ROLE_TEMPS.get(role_type, 0.70)
        model_name = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
        if "/" not in model_name:
            model_name = f"deepseek/{model_name}"

        return LLM(
            model=model_name,
            base_url=os.getenv("OPENAI_API_BASE", "https://api.deepseek.com"),
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            temperature=temp,
        )
