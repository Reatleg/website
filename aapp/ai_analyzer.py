import os
import base64
from openai import OpenAI
from typing import Dict, List, Optional
from PIL import Image
import io

class FuryTraderAI:
    """AI-powered trading analysis using GPT-4 Vision"""
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build the comprehensive system prompt for the AI"""
        return """You are an elite Price Action trading analyst specializing in FX markets. Your role is to analyze charts and provide actionable trading scenarios.

**ANALYSIS FRAMEWORK:**

1. **Market Structure (The Snake Trick - Optional)**
   - Identify trend direction using body closes only (HH/HL for uptrend, LH/LL for downtrend)
   - Note: This is a confluence tool, not a requirement

2. **Chart Patterns (Powerful Confluence)**
   - Look for Head & Shoulders, Double Tops/Bottoms, Neckline Retests
   - These add significant weight but are NOT mandatory for valid setups

3. **Supply & Demand Zones (AOI - Critical)**
   - Identify areas of interest based on last indecision candles
   - HIGH PRIORITY: Zones MUST have Fair Value Gaps (FVG) for quality
   - Mark clear entry, stop loss, and take profit zones

4. **Momentum Analysis**
   - Analyze candle bodies vs wicks to determine control
   - Look for strong rejection wicks, engulfing patterns, and momentum shifts

5. **Multi-Timeframe Context**
   - Primary: Analyze HTF (Daily/4H) for overall bias
   - Secondary: Analyze 1H for entry refinement
   - If lower timeframes provided (15m, 10m, 5m): Use for precise "sniper" entries

**OUTPUT FORMAT:**

Provide analysis in this exact structure:

**PAIR:** [Currency Pair]
**VERDICT:** [YES/NO/WAIT]
**CONFIDENCE:** [1-10]
**SETUP TYPE:** [Gap/Day/Continuation]

**MARKET STORY:**
[2-3 sentences describing the overall market narrative]

**KEY CONFLUENCES:**
- [List 3-5 confluences found]
- [Include FVG presence, structure, patterns if present]

**SCENARIO A - THE PRIMARY (Limit Order)**
- Entry: [Exact price level]
- Stop Loss: [Exact price level]
- Take Profit: [Exact price level]
- Logic: [Why this is the highest probability setup]
- Risk/Reward: [Calculate R:R ratio]

**SCENARIO B - THE AGGRESSIVE (Alert/Confirmation)**
- Trigger: [Specific price action confirmation needed]
- Entry: [Price level after confirmation]
- Stop Loss: [Exact price level]
- Take Profit: [Exact price level]
- Logic: [When to take this instead of Scenario A]

**SCENARIO C - INVALIDATION (Wait/Exit)**
- Invalidation Level: [Exact price that kills the setup]
- Warning Signs: [What price action to watch for]
- Alternative: [What to wait for if this fails]

**CRITICAL LEVELS:**
- Support: [List key support levels]
- Resistance: [List key resistance levels]

Be specific, actionable, and honest. If confluences are weak, say WAIT."""

    def encode_image(self, image_path: str) -> str:
        """Convert image to base64 for API"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def encode_image_from_bytes(self, image_bytes: bytes) -> str:
        """Convert image bytes to base64"""
        return base64.b64encode(image_bytes).decode('utf-8')
    
    def analyze_chart(self, images: List[bytes], pair: str, timeframes: List[str], 
                      user_context: Optional[str] = None) -> Dict:
        """
        Analyze trading charts and provide scenarios
        
        Args:
            images: List of image bytes (HTF, 1H, optional LTF)
            pair: Currency pair (e.g., "GBP/CAD")
            timeframes: List of timeframes for each image
            user_context: Optional additional context from user
            
        Returns:
            Dictionary with analysis results
        """
        
        # Prepare image messages
        image_messages = []
        for idx, img_bytes in enumerate(images):
            base64_image = self.encode_image_from_bytes(img_bytes)
            tf = timeframes[idx] if idx < len(timeframes) else "Unknown"
            image_messages.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}",
                    "detail": "high"
                }
            })
            image_messages.append({
                "type": "text",
                "text": f"[Chart {idx+1}: {tf} timeframe]"
            })
        
        # Build the user message
        user_message_text = f"""Analyze this {pair} setup across the provided timeframes.

**Timeframes provided:** {', '.join(timeframes)}

**User Context:** {user_context if user_context else 'None provided'}

Please provide a complete analysis following the framework."""

        # Combine text and images
        messages = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_message_text}
                ] + image_messages
            }
        ]
        
        try:
            # Call GPT-4 Vision
            response = self.client.chat.completions.create(
                model="gpt-4o",  # Use gpt-4o for vision capabilities
                messages=messages,
                max_tokens=2000,
                temperature=0.7
            )
            
            analysis_text = response.choices[0].message.content
            
            # Parse the response into structured data
            parsed = self._parse_analysis(analysis_text, pair)
            
            return {
                'success': True,
                'raw_analysis': analysis_text,
                'parsed': parsed,
                'pair': pair,
                'timeframes': timeframes
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'pair': pair,
                'timeframes': timeframes
            }
    
    def _parse_analysis(self, text: str, pair: str) -> Dict:
        """Parse AI response into structured data"""
        
        lines = text.split('\n')
        parsed = {
            'pair': pair,
            'verdict': 'UNKNOWN',
            'confidence': 5,
            'setup_type': 'Unknown',
            'market_story': '',
            'confluences': [],
            'scenario_a': {},
            'scenario_b': {},
            'scenario_c': {},
            'key_levels': {}
        }
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            # Extract key fields
            if 'VERDICT:' in line.upper():
                parsed['verdict'] = line.split(':', 1)[1].strip()
            elif 'CONFIDENCE:' in line.upper():
                try:
                    conf_str = line.split(':', 1)[1].strip()
                    parsed['confidence'] = int(''.join(filter(str.isdigit, conf_str)))
                except:
                    pass
            elif 'SETUP TYPE:' in line.upper():
                parsed['setup_type'] = line.split(':', 1)[1].strip()
            
            # Track sections
            elif 'MARKET STORY' in line.upper():
                current_section = 'story'
            elif 'KEY CONFLUENCES' in line.upper():
                current_section = 'confluences'
            elif 'SCENARIO A' in line.upper():
                current_section = 'scenario_a'
            elif 'SCENARIO B' in line.upper():
                current_section = 'scenario_b'
            elif 'SCENARIO C' in line.upper():
                current_section = 'scenario_c'
            elif 'CRITICAL LEVELS' in line.upper():
                current_section = 'levels'
            
            # Collect section content
            elif line and current_section:
                if current_section == 'story':
                    parsed['market_story'] += line + ' '
                elif current_section == 'confluences' and line.startswith('-'):
                    parsed['confluences'].append(line[1:].strip())
                elif current_section in ['scenario_a', 'scenario_b', 'scenario_c']:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        parsed[current_section][key.strip().lower().replace(' ', '_')] = value.strip()
        
        return parsed
    
    def quick_verdict(self, image_bytes: bytes, pair: str, question: str) -> str:
        """
        Quick analysis for simple questions
        """
        base64_image = self.encode_image_from_bytes(image_bytes)
        
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"You are a trading analyst. For {pair}, answer this question briefly: {question}"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "low"
                        }
                    }
                ]
            }
        ]
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=300
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {str(e)}"