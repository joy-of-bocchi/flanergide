"""LLM prompt templates for summarization generation."""


DAILY_ANALYSIS_PROMPT = """You are analyzing one day in someone's life based on their phone activity and blog posts.

Below is the accumulated data from their phone (text captured from apps) and any blog posts they published that day.

====================================
DATA FROM {date}
====================================

{data}

====================================
END OF DATA
====================================

Your task is to provide a comprehensive analysis across 4 dimensions. Be specific, evidence-based, and honest.

Generate a markdown document with the following structure:

# Daily Summary - {date}

## What You Did Today
Analyze their actual activities based on app usage and text content. Focus on:
- What apps they used and for what purpose
- Time allocation (if inferable from timestamps)
- Key tasks or projects worked on
- Social interactions
- Productivity vs leisure balance

Be specific with examples from the data. Use bullet points for clarity.

## What Was On Your Mind
Extract the dominant topics, themes, and concerns from their text. Look for:
- Recurring themes or topics
- Questions they asked or researched
- Problems they were trying to solve
- Interests or curiosities
- Work-related vs personal thoughts

Quote or reference specific text when relevant.

## Mood Analysis
Analyze their emotional state throughout the day. Consider:
- Overall mood (energetic, tired, stressed, calm, anxious, happy, etc.)
- Emotional tone in their language (formal, casual, terse, expressive)
- Variations in mood (if timestamps show progression)
- Stressors or positive triggers
- Energy levels

Base this on language patterns, word choice, punctuation, message length, etc.

## Personality Insights
Based on their behavior and communication patterns, what can you infer about:
- Communication style (direct, verbose, technical, casual)
- Cognitive patterns (detail-oriented vs big-picture, analytical vs intuitive)
- Social tendencies (introverted/extroverted patterns)
- Work style (focused sessions, multitasking, procrastination)
- Values and priorities (what gets their time and attention)

Look for patterns that reveal consistent traits, not just one-off behaviors.

---
**Important Guidelines:**
- Be honest and observational, not judgmental
- Use specific evidence from the data
- If data is limited, acknowledge it
- Avoid making up details not in the data
- Keep each section to 3-5 bullet points or 1-2 paragraphs

Generate only the markdown output, no preamble or explanation.
"""


WEEKLY_ANALYSIS_PROMPT = """You are analyzing a week in someone's life based on their phone activity and blog posts.

Below is the accumulated data from their phone (text captured from apps) and any blog posts they published during this period.

====================================
DATA FROM {start_date} TO {end_date}
====================================

{data}

====================================
END OF DATA
====================================

Your task is to provide a comprehensive weekly analysis across 4 dimensions. Look for patterns, trends, and changes over the week.

Generate a markdown document with the following structure:

# Weekly Summary - {start_date} to {end_date}

## What You Did This Week
Analyze their activities and time allocation over the week. Focus on:
- Major activities and projects
- Day-to-day patterns (weekday vs weekend differences)
- Productivity trends
- Social interactions and relationships
- Balance between work, learning, socializing, and leisure
- Notable events or milestones

Organize chronologically or thematically as makes sense. Use bullet points and examples.

## What Was On Your Mind
Extract dominant themes and intellectual preoccupations over the week. Look for:
- Main topics of focus (what kept coming up?)
- Evolution of thoughts (did interests shift during the week?)
- Problems they were working through
- Learning or research areas
- Recurring concerns or anxieties
- Aspirations or goals mentioned

Show how topics evolved or persisted across days.

## Mood Analysis
Analyze emotional patterns throughout the week. Consider:
- Overall weekly mood trend (improving, declining, stable)
- Day-to-day variations in mood
- Best and worst days (emotionally)
- Stressors and what triggered them
- Sources of joy or satisfaction
- Energy levels and fatigue patterns
- Weekend vs weekday emotional differences

Look for cause-effect patterns (e.g., "mood improved after...").

## Personality Insights
Based on a week of behavior, what patterns reveal about their personality:
- Consistent behavioral traits observed across multiple days
- How they handle stress or challenges
- Communication and social patterns
- Work habits and productivity style
- Decision-making patterns
- What they prioritize when free to choose
- Growth or change observed during the week

Compare beginning and end of week for any notable shifts.

---
**Important Guidelines:**
- Focus on patterns and trends, not isolated incidents
- Compare different parts of the week to show contrast
- Use specific examples to support observations
- Be honest and constructive
- Acknowledge if certain days have more/less data
- Keep analysis grounded in evidence from the data
- Each section should be 2-4 paragraphs or organized bullet points

Generate only the markdown output, no preamble or explanation.
"""


def format_daily_prompt(date: str, data: str) -> str:
    """Format the daily analysis prompt with data.

    Args:
        date: Date in YYYY-MM-DD format
        data: Accumulated log data and blog posts

    Returns:
        Formatted prompt ready for LLM
    """
    return DAILY_ANALYSIS_PROMPT.format(date=date, data=data)


def format_weekly_prompt(start_date: str, end_date: str, data: str) -> str:
    """Format the weekly analysis prompt with data.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        data: Accumulated log data and blog posts

    Returns:
        Formatted prompt ready for LLM
    """
    return WEEKLY_ANALYSIS_PROMPT.format(
        start_date=start_date,
        end_date=end_date,
        data=data
    )
