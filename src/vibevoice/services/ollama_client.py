"""
Ollama client service for LLM script generation.
"""
import logging
from typing import Optional

import httpx

from ..config import config

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for interacting with Ollama API."""

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Ollama client.

        Args:
            base_url: Ollama server base URL (defaults to config)
            model: Ollama model name (defaults to config)
        """
        self.base_url = base_url or config.OLLAMA_BASE_URL
        self.model = model or config.OLLAMA_MODEL
        self.timeout = 300  # 5 minutes for long-running requests
        self.client = httpx.Client(timeout=self.timeout)

        logger.info(f"OllamaClient initialized: {self.base_url}, model: {self.model}")

    def check_connection(self) -> bool:
        """
        Check if Ollama server is accessible.

        Returns:
            True if server is accessible, False otherwise
        """
        try:
            response = self.client.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.warning(f"Ollama connection check failed: {e}")
            return False

    def generate_script(
        self,
        article_text: str,
        genre: str,
        duration: str,
        num_voices: int,
        custom_model: Optional[str] = None,
    ) -> str:
        """
        Generate podcast script from article using Ollama.

        Args:
            article_text: Scraped article content
            genre: Podcast genre (Comedy, Serious, News, etc.)
            duration: Target duration (e.g., "5 min", "30 min")
            num_voices: Number of voices/speakers (1-4)
            custom_model: Optional custom model name (overrides default)

        Returns:
            Generated podcast script with speaker labels

        Raises:
            RuntimeError: If Ollama request fails
        """
        model = custom_model or self.model

        # Truncate article if too long (keep first ~8000 chars for context)
        max_article_length = 8000
        if len(article_text) > max_article_length:
            logger.info(f"Truncating article from {len(article_text)} to {max_article_length} characters")
            article_text = article_text[:max_article_length] + "\n[... article truncated ...]"

        # Build prompt for script generation
        prompt = self._build_prompt(article_text, genre, duration, num_voices)

        logger.info(f"Generating script with Ollama (model: {model}, genre: {genre}, duration: {duration})")

        try:
            response = self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                    },
                },
            )
            response.raise_for_status()

            result = response.json()
            script = result.get("response", "").strip()

            if not script:
                raise RuntimeError("Ollama returned empty script")

            # Clean up the script
            script = self._clean_script(script, num_voices)

            logger.info(f"Generated script: {len(script)} characters")
            return script

        except httpx.HTTPError as e:
            error_msg = f"Ollama API request failed: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error during script generation: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def _build_prompt(self, article_text: str, genre: str, duration: str, num_voices: int) -> str:
        """
        Build prompt for Ollama script generation.

        Args:
            article_text: Article content
            genre: Podcast genre
            duration: Target duration
            num_voices: Number of voices

        Returns:
            Formatted prompt string
        """
        # Map duration to approximate word count
        duration_map = {
            "5 min": "500-700 words",
            "10 min": "1000-1400 words",
            "15 min": "1500-2100 words",
            "30 min": "3000-4200 words",
        }
        word_target = duration_map.get(duration, "1000-1400 words")

        # Genre-specific instructions
        genre_instructions = {
            "Comedy": "Make it light-hearted, humorous, and engaging. Include jokes and witty commentary.",
            "Serious": "Keep it professional, informative, and thoughtful. Maintain a serious tone throughout.",
            "News": "Present information clearly and objectively. Use a journalistic style with facts and analysis.",
            "Educational": "Focus on teaching and explaining concepts clearly. Use examples and analogies.",
            "Storytelling": "Narrate the content as a story with engaging descriptions and narrative flow.",
            "Interview": "Format as a conversation with questions and answers. Make it feel like a natural interview.",
            "Documentary": "Present information in a documentary style with detailed explanations and context.",
        }
        genre_style = genre_instructions.get(genre, "Keep it informative and engaging.")

        # Build speaker labels based on num_voices
        speaker_examples = []
        for i in range(1, num_voices + 1):
            speaker_examples.append(f"Speaker {i}: [dialogue here]")

        prompt = f"""You are a professional podcast script writer. Create a podcast script based on the following article.

Article Content:
{article_text}

Requirements:
- Genre: {genre}
- Style: {genre_style}
- Target length: {word_target} (approximately {duration})
- Number of speakers: {num_voices}
- Format: Use "Speaker 1:", "Speaker 2:", etc. to indicate different speakers

Format the script exactly like this example:
{chr(10).join(speaker_examples)}

Guidelines:
1. Distribute dialogue evenly among all {num_voices} speakers
2. Make the conversation natural and engaging
3. Cover the main points of the article
4. Adapt the style to match the {genre} genre
5. Ensure the script is approximately {duration} long when read at a normal pace
6. Start with an introduction and end with a conclusion
7. Use clear speaker labels: "Speaker 1:", "Speaker 2:", etc.

Generate the podcast script now:"""

        return prompt

    def _clean_script(self, script: str, num_voices: int) -> str:
        """
        Clean and format generated script.

        Args:
            script: Raw script from Ollama
            num_voices: Expected number of voices

        Returns:
            Cleaned script
        """
        # Remove markdown code blocks if present
        if script.startswith("```"):
            lines = script.split("\n")
            # Remove first line if it's ``` or ```markdown
            if lines[0].strip().startswith("```"):
                lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            script = "\n".join(lines)

        # Ensure proper speaker labels
        lines = script.split("\n")
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if line starts with a speaker label
            has_speaker = any(line.startswith(f"Speaker {i}:") for i in range(1, num_voices + 1))

            if not has_speaker and cleaned_lines:
                # If previous line was a speaker line, append to it
                if cleaned_lines and any(cleaned_lines[-1].startswith(f"Speaker {i}:") for i in range(1, num_voices + 1)):
                    cleaned_lines[-1] += " " + line
                    continue

            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def __del__(self):
        """Clean up HTTP client."""
        if hasattr(self, "client"):
            self.client.close()


# Global Ollama client instance
ollama_client = OllamaClient()
