"""
AI Tools Module - The AI-Powered Research Assistant
==================================================

This module serves as Easely's interface to external AI services, specifically
designed to generate structured assignment outlines for premium users.

Core Responsibilities:
- Prompt engineering for academic assignment analysis
- API interaction with OpenAI's GPT models
- Response parsing and cleaning
- Robust error handling for AI service interactions

Author: Easely Development Team
"""

import openai
import logging
from typing import Optional, Dict, Any
from config.settings import OPENAI_API_KEY

# Configure logging
logger = logging.getLogger(__name__)

class AIServiceError(Exception):
    """Custom exception for AI service related errors"""
    pass

class AITools:
    """
    AI-Powered Research Assistant for generating assignment outlines
    """
    
    def __init__(self):
        """Initialize the AI tools with API configuration"""
        if not OPENAI_API_KEY:
            raise AIServiceError("OpenAI API key not found in configuration")
        
        openai.api_key = OPENAI_API_KEY
        self.model = "gpt-3.5-turbo"  # Cost-effective model for outline generation
        self.max_tokens = 800  # Reasonable limit for outline responses
        self.temperature = 0.7  # Balanced creativity and structure
    
    def _create_outline_prompt(self, assignment_title: str, assignment_description: str) -> str:
        """
        Engineer a high-quality prompt for assignment outline generation
        
        Args:
            assignment_title (str): The title of the assignment
            assignment_description (str): Detailed assignment description
            
        Returns:
            str: Engineered prompt for the AI model
        """
        prompt = f"""You are a helpful academic assistant specializing in creating structured outlines for student assignments. Your goal is to help students break down complex assignments into manageable, actionable steps.

Assignment Title: {assignment_title}

Assignment Description: {assignment_description}

Please create a clear, structured outline that includes:

1. **Main Topic Analysis**: Brief interpretation of what the assignment is asking for
2. **Key Components**: Break down the assignment into 3-5 main sections or arguments
3. **Suggested Structure**: Provide a logical flow for the work
4. **Research Guidance**: Suggest 2-3 types of sources or research directions
5. **Action Steps**: List 3-4 concrete next steps the student should take to get started

Format your response as a clean, organized outline using bullet points and clear headings. Keep it concise but comprehensive - aim for practical guidance that reduces the student's cognitive load and helps them overcome the initial hurdle of starting their work.

Focus on being actionable and specific rather than generic. Avoid unnecessary introductory phrases like "Certainly!" or "Here's your outline:" - jump straight into the helpful content."""

        return prompt
    
    def _clean_ai_response(self, raw_response: str) -> str:
        """
        Clean and format the AI response for direct user consumption
        
        Args:
            raw_response (str): Raw response from AI service
            
        Returns:
            str: Cleaned and formatted response
        """
        # Remove common conversational fluff
        fluff_phrases = [
            "Certainly!",
            "Here's your outline:",
            "Here is the outline you requested:",
            "I'd be happy to help you with that.",
            "Based on your assignment, here's",
            "Here's a structured outline for your assignment:"
        ]
        
        cleaned = raw_response.strip()
        
        # Remove fluff phrases (case-insensitive)
        for phrase in fluff_phrases:
            cleaned = cleaned.replace(phrase, "").strip()
        
        # Remove multiple consecutive newlines
        while "\n\n\n" in cleaned:
            cleaned = cleaned.replace("\n\n\n", "\n\n")
        
        # Ensure the response starts cleanly
        cleaned = cleaned.lstrip("\n").strip()
        
        return cleaned
    
    def _make_ai_request(self, prompt: str) -> str:
        """
        Make the actual API request to OpenAI
        
        Args:
            prompt (str): The engineered prompt to send
            
        Returns:
            str: Raw response from AI service
            
        Raises:
            AIServiceError: If the API request fails
        """
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful academic assistant who creates structured, actionable assignment outlines."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            
            if not response.choices:
                raise AIServiceError("No response generated by AI service")
            
            return response.choices[0].message.content.strip()
            
        except openai.error.RateLimitError:
            logger.error("OpenAI rate limit exceeded")
            raise AIServiceError("AI service is currently overloaded. Please try again in a few minutes.")
        
        except openai.error.InvalidRequestError as e:
            logger.error(f"Invalid OpenAI request: {e}")
            raise AIServiceError("Invalid request to AI service. Please try again.")
        
        except openai.error.AuthenticationError:
            logger.error("OpenAI authentication failed")
            raise AIServiceError("AI service authentication failed. Please contact support.")
        
        except openai.error.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise AIServiceError("AI service is temporarily unavailable. Please try again later.")
        
        except Exception as e:
            logger.error(f"Unexpected error in AI request: {e}")
            raise AIServiceError("An unexpected error occurred. Please try again.")
    
    def generate_assignment_outline(self, assignment_title: str, assignment_description: str) -> str:
        """
        Generate a structured outline for a given assignment
        
        This is the main public function that orchestrates the entire AI outline
        generation process. It handles prompt engineering, API interaction,
        response cleaning, and error handling.
        
        Args:
            assignment_title (str): The title of the assignment
            assignment_description (str): Detailed description of the assignment
            
        Returns:
            str: Clean, formatted outline ready to send to user
            
        Raises:
            AIServiceError: If outline generation fails
        """
        # Validate inputs
        if not assignment_title or not assignment_title.strip():
            raise AIServiceError("Assignment title is required for outline generation")
        
        if not assignment_description or not assignment_description.strip():
            raise AIServiceError("Assignment description is required for outline generation")
        
        try:
            # Step 1: Engineer the prompt
            logger.info(f"Generating outline for assignment: {assignment_title[:50]}...")
            prompt = self._create_outline_prompt(assignment_title.strip(), assignment_description.strip())
            
            # Step 2: Make API request
            raw_response = self._make_ai_request(prompt)
            
            # Step 3: Clean and format response
            cleaned_response = self._clean_ai_response(raw_response)
            
            # Validate the cleaned response
            if not cleaned_response or len(cleaned_response) < 50:
                logger.warning("AI response appears too short or empty")
                raise AIServiceError("Generated outline appears incomplete. Please try again.")
            
            logger.info("Successfully generated assignment outline")
            return cleaned_response
            
        except AIServiceError:
            # Re-raise AIServiceError as-is
            raise
        except Exception as e:
            logger.error(f"Unexpected error in outline generation: {e}")
            raise AIServiceError("Failed to generate outline. Please try again.")


# Convenience function for easy importing
def generate_assignment_outline(assignment_title: str, assignment_description: str) -> str:
    """
    Convenience function to generate an assignment outline
    
    This is the primary interface that other modules should use.
    
    Args:
        assignment_title (str): The title of the assignment
        assignment_description (str): Detailed description of the assignment
        
    Returns:
        str: Clean, formatted outline ready to send to user
        
    Raises:
        AIServiceError: If outline generation fails
    """
    ai_tools = AITools()
    return ai_tools.generate_assignment_outline(assignment_title, assignment_description)


# Example usage and testing functions
if __name__ == "__main__":
    """
    Basic testing functionality - only runs when script is executed directly
    """
    # Example test case
    sample_title = "Essay on The Great Gatsby"
    sample_description = """
    Analyze the theme of the American Dream in F. Scott Fitzgerald's 'The Great Gatsby'. 
    Your essay should be 5 pages long, double-spaced, and include at least 4 scholarly sources. 
    Focus on how different characters represent different aspects of the American Dream and 
    discuss whether Fitzgerald presents the dream as achievable or as an illusion.
    Due date: Next Friday at 11:59 PM.
    """
    
    try:
        outline = generate_assignment_outline(sample_title, sample_description)
        print("Generated Outline:")
        print("=" * 50)
        print(outline)
        print("=" * 50)
    except AIServiceError as e:
        print(f"Error generating outline: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")