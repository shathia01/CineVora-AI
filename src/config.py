from __future__ import annotations

APP_NAME = "CineVora AI"
APP_TAGLINE = "Understand your story. Improve your script."
MAX_SCRIPT_CHARS = 1_500_000
MAX_SCENE_ANALYSIS = 12
MAX_CHARACTERS = 8

SCRIPT_TYPES = ["Auto Detect", "Short Film", "Feature Film", "Web Series", "Pilot"]
LANGUAGES = ["Auto Detect", "English", "Tamil", "Tanglish", "Bahasa Malaysia", "Other"]

LEARNING_TOPICS = {
    "Story Structure": {
        "definition": "The way major story events are arranged from the beginning to the ending.",
        "example": "A student wants to win a film competition, faces a setback, changes approach, and finally presents the film.",
        "mistake": "Adding events without a clear change in conflict or direction.",
        "tip": "Ask what changes for the main character after each major section.",
    },
    "Turning Point": {
        "definition": "A moment that changes the direction of the story or the character's choices.",
        "example": "The protagonist discovers that the person helping them has been hiding the truth.",
        "mistake": "A big event happens, but nothing changes afterward.",
        "tip": "A turning point should create a new decision, problem, or direction.",
    },
    "Character Motivation": {
        "definition": "The reason a character wants something or chooses to act.",
        "example": "Goal: win the competition. Motivation: the prize pays the student's next semester fees.",
        "mistake": "The character has a goal, but the audience does not understand why it matters.",
        "tip": "Ask: Why does this matter personally to the character?",
    },
    "Character Arc": {
        "definition": "How a character changes from the beginning of the story to the end.",
        "example": "Avoids conflict → faces consequences → learns to speak up.",
        "mistake": "The story changes, but the main character stays emotionally unchanged without a reason.",
        "tip": "Compare the character's first important choice with their final important choice.",
    },
    "Dialogue": {
        "definition": "What characters say, including what they reveal, hide, avoid, or imply.",
        "example": "Instead of explaining fear directly, a character may answer with short sentences and avoid eye contact.",
        "mistake": "Characters explain information that both of them already know just for the audience.",
        "tip": "Read dialogue aloud. If it sounds like an essay, shorten or dramatize it.",
    },
    "Exposition": {
        "definition": "Information the audience needs to understand the story, world, or past events.",
        "example": "A brief line reveals that two friends have not spoken since last semester.",
        "mistake": "Giving too much background information in one speech.",
        "tip": "Spread information across action, conflict, visuals, and shorter lines.",
    },
    "Pacing": {
        "definition": "How quickly or slowly the story feels like it is moving.",
        "example": "A tense chase usually feels faster than a long conversation repeating the same idea.",
        "mistake": "Keeping scenes after their main purpose is already complete.",
        "tip": "Ask whether every scene changes information, emotion, conflict, or direction.",
    },
    "Show vs Tell": {
        "definition": "Showing lets the audience understand through actions, visuals, behaviour, and sound instead of direct explanation.",
        "example": "Instead of saying 'I'm nervous,' a character keeps checking the door and cannot hold the pen steadily.",
        "mistake": "Dialogue explains an emotion that the audience can already see.",
        "tip": "Ask whether the camera could communicate the same idea without the line.",
    },
    "Screenplay Formatting": {
        "definition": "The standard way scene headings, action, character cues, dialogue, and other screenplay elements are presented.",
        "example": "INT. LIBRARY – DAY, followed by action, then a character cue and dialogue.",
        "mistake": "Mixing action and dialogue together so it becomes difficult to identify who says what.",
        "tip": "Formatting should improve readability; it should not replace good storytelling.",
    },
}
